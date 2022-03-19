# import _thread
import os
import datetime
import json

os.environ['EVENTLET_NO_GREENDNS'] = 'yes'
from eventlet import tpool
import socketio
from libs import iEEG
from libs.iEEG import ReadError, WriteError, metadata as metadata_fields
from libs.Modifier import Modifier
from libs import BIDS
from libs import loris_api as la

# Create socket listener.
# sio = socketio.Server(async_mode='eventlet', cors_allowed_origins=[])
# app = socketio.WSGIApp(sio)

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[])
app = socketio.ASGIApp(sio)


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

    async with sio.session(sid) as session:
        candidate = la.get_candidate(data['candID'], session['lorisURL'], session['lorisToken'])
    await sio.emit('participant_data', candidate, sid)


@sio.event
async def set_loris_credentials(sid, data):
    if 'lorisURL' not in data:
        print('error with credentials:', data)
        return

    if data['lorisURL'].endswith('/'):
        data['lorisURL'] = data['lorisURL'][:-1]
    url = data['lorisURL'] + '/api/v0.0.4-dev/'
    username = data['lorisUsername']
    password = data['lorisPassword']
    resp = la.login(url, username, password)
    token = resp['token']

    if resp.get('error'):
        await sio.emit('loris_login_response', {'error': resp.get('error')}, sid)
    else:
        async with sio.session(sid) as session:
            session['lorisURL'] = url
            session['lorisUsername'] = username
            session['lorisToken'] = resp['token']

            await sio.emit(
                'loris_login_response',
                {
                    'success': 200,
                    'lorisUsername': username
                }, sid
            )

            await sio.emit('loris_sites', la.get_sites(url, token), sid)
            await sio.emit('loris_projects', la.get_projects(url, token), sid)


@sio.event
async def get_loris_sites(sid):
    async with sio.session(sid) as session:
        await sio.emit('loris_sites', la.get_sites(session['lorisURL'], session['lorisToken']), sid)


@sio.event
async def get_loris_projects(sid):
    async with sio.session(sid) as session:
        await sio.emit('loris_projects', la.get_projects(session['lorisURL'], session['lorisToken']), sid)


@sio.event
async def get_loris_subprojects(sid, project):
    async with sio.session(sid) as session:
        await sio.emit('loris_subprojects', la.get_subprojects(project, session['lorisURL'], session['lorisToken']),
                       sid)


@sio.event
async def get_loris_visits(sid, subproject):
    async with sio.session(sid) as session:
        await sio.emit('loris_visits', la.get_visits(subproject, session['lorisURL'], session['lorisToken']), sid)


@sio.event
async def create_visit(sid, data):
    async with sio.session(sid) as session:
        la.create_visit(
            data['candID'],
            data['visit'],
            data['site'],
            data['project'],
            data['subproject'],
            session['lorisURL'],
            session['lorisToken']
        )

        la.start_next_stage(
            data['candID'],
            data['visit'],
            data['site'],
            data['subproject'],
            data['project'],
            data['date'],
            session['lorisURL'],
            session['lorisToken']
        )


@sio.event
async def create_candidate_and_visit(sid, data):
    async with sio.session(sid) as session:
        new_candidate = la.create_candidate(
            data['project'],
            data['dob'],
            data['sex'],
            data['site'],
            session['lorisURL'],
            session['lorisToken']
        )

        if new_candidate['CandID']:
            print('create_visit')

            la.create_visit(new_candidate['CandID'],
                            data['visit'],
                            data['site'],
                            data['project'],
                            data['subproject'],
                            session['lorisURL'],
                            session['lorisToken']
                            )

            la.start_next_stage(new_candidate['CandID'],
                                data['visit'],
                                data['site'],
                                data['subproject'],
                                data['project'],
                                data['date'],
                                session['lorisURL'],
                                session['lorisToken']
                                )

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
