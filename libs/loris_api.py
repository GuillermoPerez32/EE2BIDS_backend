import json
import requests
import urllib


def login(url, username, password):
    resp = requests.post(
        url=url + 'login',
        json={
            'username': username,
            'password': password
        },
        verify=False
    )

    print(resp)

    login_succeeded = {}
    if resp.status_code == 405:
        login_succeeded = {'error': 'User credentials error!'}
        print('User credentials error!')
    else:
        resp_json = json.loads(resp.content.decode('ascii'))
        print(resp_json)
        if resp_json.get('error'):
            login_succeeded = {'error': resp_json.get('error')}
        else:
            token = resp_json.get('token')
            print(token)
            login_succeeded = {'token': token}
    return login_succeeded


def get_projects(url, token):
    print('get_projects has ran')
    resp = requests.get(
        url=url + 'projects',
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )

    json_resp = json.loads(resp.content.decode('ascii'))
    return json_resp.get('Projects')


def get_all_subprojects(url, token):
    print('get_all_subprojects has ran')
    resp = requests.get(
        url=url + 'subprojects',
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )
    print('getting subprojects')
    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    return json_resp.get('Subprojects')


def get_subprojects(project, url, token):
    print('get_subprojects has ran')
    project = get_project(project, url, token)
    print(project)
    return project.get('Subprojects')


def get_visits(subproject, url, token):
    print('get_visits has ran')
    print('get_visits look here:')
    resp = requests.get(
        url=url + 'subprojects/' + urllib.parse.quote(subproject),
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )

    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    print(json_resp)
    return json_resp.get('Visits')


def get_sites(url, token):
    print('get_sites has ran')
    resp = requests.get(
        url=url + 'sites',
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )

    print(resp)

    json_resp = json.loads(resp.content.decode('ascii'))
    print(json_resp)
    sites = json_resp.get('Sites')
    return sites


def get_project(project, url, token):
    print('get_project has ran')
    resp = requests.get(
        url=url + 'projects/' + urllib.parse.quote(project),
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )

    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    return json_resp


def get_visit(candid, visit, site, subproject, project, url, token):
    print('get_visit has ran')
    resp = requests.get(
        url=url + '/candidates/' + str(candid) + '/' + urllib.parse.quote(visit),
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        data=json.dumps({
            "Meta": {
                "CandID": candid,
                "Visit": visit,
                "Site": site,
                "Battery": subproject,
                "Project": project
            }
        }),
        verify=False
    )

    print(visit)
    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    return json_resp


def start_next_stage(candid, visit, site, subproject, project, date, url, token):
    print('start_next_stage has ran')
    resp = requests.patch(
        url=url + '/candidates/' + str(candid) + '/' + urllib.parse.quote(visit),
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        data=json.dumps({
            "CandID": candid,
            "Visit": visit,
            "Site": site,
            "Battery": subproject,
            "Project": project,
            "Stages": {
                "Visit": {
                    "Date": date,
                    "Status": "In Progress",
                }
            }
        }),
        verify=False
    )
    print('resp.status_code:')
    print(resp.status_code)
    print('resp.text:')
    print(resp.text)


def create_candidate(project, dob, sex, site, url, token):
    print('create_candidate has ran')
    resp = requests.post(
        url=url + '/candidates/',
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        data=json.dumps({
            "Candidate": {
                "Project": project,
                "DoB": dob,
                "Sex": sex,
                "Site": site,
            }
        }),
        verify=False
    )

    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    print(json_resp)
    return json_resp


def create_visit(candid, visit, site, project, subproject, url, token):
    print('create_visit has ran')
    resp = requests.put(
        url=url + '/candidates/' + candid + '/' + visit,
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        data=json.dumps({
            "CandID": candid,
            "Visit": visit,
            "Site": site,
            "Battery": subproject,
            "Project": project
        }),
        verify=False
    )
    print('resp:')
    print(resp)
    # json_resp = json.loads(resp.content.decode('ascii'))
    # print(json_resp)


def get_candidate(candid, url, token):
    print('get_candidate has ran')
    resp = requests.get(
        url=url + '/candidates/' + candid,
        headers={'Authorization': 'Bearer %s' % token, 'LORIS-Overwrite': 'overwrite'},
        verify=False
    )

    print(resp)
    json_resp = json.loads(resp.content.decode('ascii'))
    print(json_resp)

    # validate candid
    if json_resp.get('error'):
        return {'error': 'DCCID is not valid.'}

    return json_resp.get('Meta')
