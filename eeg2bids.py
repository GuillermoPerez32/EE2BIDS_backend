# import _thread
import os
import logging
import asyncio
import uvicorn
from uvicorn.loops.asyncio import asyncio_setup
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'
import eventlet
from eventlet import tpool
import socketio
from libs import iEEG
from libs.iEEG import ReadError, WriteError, metadata as metadata_fields
from libs.Modifier import Modifier
from libs import BIDS
from libs.loris_api import LorisAPI
import csv
import datetime
import json

# LORIS credentials of user
lorisCredentials = {
    'lorisURL': '',
    'lorisUsername': '',
    'lorisPassword': '',
}

# Create socket listener.
# sio = socketio.Server(async_mode='eventlet', cors_allowed_origins=[])
# app = socketio.WSGIApp(sio)

sio = socketio.AsyncServer(async_mode = 'asgi', cors_allowed_origins=[])
app = socketio.ASGIApp(sio)

# Create Loris API handler.
loris_api = LorisAPI()


@sio.event
async def connect(sid, environ):
    print(f'connect: {sid}')

def tarfile_bids_thread(bids_directory):
    iEEG.TarFile(bids_directory)
    response = {
        'compression_time': 'example_5mins'
    }
    return tpool.Proxy(response)


@sio.event
async def tarfile_bids(sid, bids_directory):
    response = tpool.execute(tarfile_bids_thread, bids_directory)
    send = {
        'compression_time': response['compression_time']
    }
    await sio.emit('response', send, sid)


@sio.event
async def get_participant_data(sid, data):
    # todo helper to to data validation
    if 'candID' not in data or not data['candID']:
        return

    candidate = loris_api.get_candidate(data['candID'])
    await sio.emit('participant_data', candidate, sid)


@sio.event
async def set_loris_credentials(sid, data):
    global lorisCredentials
    lorisCredentials = data
    if 'lorisURL' not in lorisCredentials:
        print('error with credentials:', data)
        return

    if lorisCredentials['lorisURL'].endswith('/'):
        lorisCredentials['lorisURL'] = lorisCredentials['lorisURL'][:-1]
    loris_api.url = lorisCredentials['lorisURL'] + '/api/v0.0.4-dev/'
    loris_api.username = lorisCredentials['lorisUsername']
    loris_api.password = lorisCredentials['lorisPassword']
    resp = loris_api.login()

    if resp.get('error'):
        await sio.emit('loris_login_response', {'error': resp.get('error')}, sid)
    else:
        await sio.emit(
        'loris_login_response', 
        {
            'success': 200,
            'lorisUsername': loris_api.username
        },sid
        )

        await sio.emit('loris_sites', loris_api.get_sites(), sid)
        await sio.emit('loris_projects', loris_api.get_projects(), sid)


@sio.event
async def get_loris_sites(sid):
    await sio.emit('loris_sites', loris_api.get_sites(), sid)


@sio.event
async def get_loris_projects(sid):
    await sio.emit('loris_projects', loris_api.get_projects(), sid)


@sio.event
async def get_loris_subprojects(sid, project):
    await sio.emit('loris_subprojects', loris_api.get_subprojects(project), sid)


@sio.event
async def get_loris_visits(sid, subproject):
    await sio.emit('loris_visits', loris_api.get_visits(subproject), sid)


@sio.event
async def create_visit(sid, data):
    loris_api.create_visit(
    data['candID'],
    data['visit'],
    data['site'],
    data['project'],
    data['subproject']
    )
    
    loris_api.start_next_stage(
    data['candID'],
    data['visit'],
    data['site'],
    data['subproject'],
    data['project'],
    data['date']
    )

@sio.event
async def create_candidate_and_visit(sid, data):
    new_candidate = loris_api.create_candidate(
        data['project'],
        data['dob'],
        data['sex'],
        data['site'],
    )

    if new_candidate['CandID']:
        print('create_visit')
        loris_api.create_visit(new_candidate['CandID'], data['visit'], data['site'], data['project'],
                            data['subproject'])

        loris_api.start_next_stage(new_candidate['CandID'], data['visit'], data['site'], data['subproject'],
                                data['project'], data['date'])

        print('new_candidate_created')
        await sio.emit('new_candidate_created', new_candidate, sid)


@sio.event
async def get_edf_data(sid, data):
    # data = { files: 'EDF files (array of {path, name})' }
    print('get_edf_data:', data)

    if 'files' not in data or not data['files']:
        msg = 'No EDF file selected.'
        print(msg)
        response = {'error': msg}
        await sio.emit('edf_data', response, sid)
        return

    headers = []
    try:
        for file in data['files']:
            anonymize = iEEG.Anonymize(file['path'])
            metadata = anonymize.get_header()
            year = '20' + str(metadata[0]['year']) if metadata[0]['year'] < 85 else '19' + str(metadata[0]['year'])
            date = datetime.datetime(int(year), metadata[0]['month'], metadata[0]['day'], metadata[0]['hour'],
                                    metadata[0]['minute'], metadata[0]['second'])

            headers.append({
                'file': file,
                'metadata': metadata,
                'date': str(date)
            })

        for i in range(1, len(headers)):
            if set(headers[i - 1]['metadata'][1]['ch_names']) != set(headers[i]['metadata'][1]['ch_names']):
                msg = 'The files selected contain more than one recording.'
                print(msg)
                response = {
                    'error': msg,
                }
                await sio.emit('edf_data', response, sid)
                return

        # sort the recording per date
        headers = sorted(headers, key=lambda k: k['date'])

        # return the first split metadata and date
        response = {
            'files': [header['file'] for header in headers],
            'subjectID': headers[0]['metadata'][0]['subject_id'],
            'recordingID': headers[0]['metadata'][0]['recording_id'],
            'date': headers[0]['date']
        }

    except ReadError as e:
        print(e)
        response = {
            'error': 'Cannot read file - ' + str(e)
        }
    except Exception as e:
        print(e)
        response = {
            'error': 'Failed to retrieve EDF header information',
        }
    await sio.emit('edf_data', response, sid)


@sio.event
async def get_bids_metadata(sid, data):
    # data = { file_path: 'path to metadata file' }
    print('data:', data)

    if 'file_path' not in data or not data['file_path']:
        msg = 'No metadata file selected.'
        print(msg)
        response = {'error': msg}
    elif 'modality' not in data or data['modality'] not in ['ieeg', 'eeg']:
        msg = 'No valid modality found.'
        print(msg)
        response = {'error': msg}
    else:
        try:
            with open(data['file_path']) as fd:
                try:
                    metadata = json.load(fd)
                    empty_values = [k for k in metadata if isinstance(metadata[k], str) and metadata[k].strip() == '']
                    diff = list(set(metadata.keys()) - set(metadata_fields[data['modality']]) - set(empty_values))
                    ignored_keys = empty_values + diff

                    response = {
                        'metadata': metadata,
                        'ignored_keys': ignored_keys,
                    }
                except ValueError as e:
                    print(e)
                    metadata = {}
                    response = {
                        'error': 'Metadata file format is not valid.',
                    }
        except IOError:
            msg = "Could not read the metadata file."
            print(msg)
            response = {
                'error': msg,
            }

    await sio.emit('bids_metadata', response, sid)


def edf_to_bids_thread(data):
    print('data is ')
    print(data)
    error_messages = []
    if 'edfData' not in data or 'files' not in data['edfData'] or not data['edfData']['files']:
        error_messages.append('No .edf file(s) to convert.')
    if 'bids_directory' not in data or not data['bids_directory']:
        error_messages.append('The BIDS output folder is missing.')
    if not data['session']:
        error_messages.append('The LORIS Visit Label is missing.')

    if not error_messages:
        time = iEEG.Time()
        data['output_time'] = 'output-' + time.latest_output

        try:
            iEEG.Converter(data)  # EDF to BIDS format.

            # store subject_id for Modifier
            data['subject_id'] = iEEG.Converter.m_info['subject_id']
            Modifier(data)  # Modifies data of BIDS format
            response = {
                'output_time': data['output_time']
            }
            return tpool.Proxy(response)
        except ReadError as e:
            error_messages.append('Cannot read file - ' + str(e))
        except WriteError as e:
            error_messages.append('Cannot write file - ' + str(e))
    else:
        response = {
            'error': error_messages
        }
    return tpool.Proxy(response)


@sio.event
async def edf_to_bids(sid, data):
    # data = { file_paths: [], bids_directory: '', read_only: false,
    # event_files: '', line_freq: '', site_id: '', project_id: '',
    # sub_project_id: '', session: '', subject_id: ''}
    print('edf_to_bids: ', data)
    response = tpool.execute(edf_to_bids_thread, data)
    print(response)
    print('Response received!')
    await sio.emit('bids', response.copy(), sid)


@sio.event
async def validate_bids(sid, bids_directory):
    print('validate_bids: ', bids_directory)
    error_messages = []
    if not bids_directory:
        error_messages.append('The BIDS output directory is missing.')

    if not error_messages:
        BIDS.Validate(bids_directory)
        response = {
            'file_paths': BIDS.Validate.file_paths,
            'result': BIDS.Validate.result
        }
    else:
        response = {
            'error': error_messages
        }
    await sio.emit('response', response, sid)


@sio.event
async def disconnect(sid):
    print('disconnect: ', sid)

# async def start_uvicorn():
#     config = uvicorn.config.Config(app, host='0.0.0.0', port=7301)
#     server = uvicorn.server.Server(config)
#     await server.serve()

# # Set up the event loop
# async def start_background_task():
#     while True:
#         logging.info(f"Background tasks that ticks every 10s.")
#         await sio.sleep(10.0)

# async def main(loop):
#     await asyncio.wait([
#         asyncio.create_task(start_uvicorn()),
#         # asyncio.create_task(start_background_task()),
#     ], return_when=asyncio.FIRST_COMPLETED)

# if __name__ == '__main__':
#     # eventlet.wsgi.server(
#     #     eventlet.listen(('127.0.0.1', 7301)),
#     #     app,
#     #     log_output=True
#     # )

#     asyncio_setup();
#     loop = asyncio.get_event_loop();
    # uvicorn.run(main(loop))
