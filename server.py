#!flask/bin/python
from flask import Flask, jsonify
from flask.ext.httpauth import HTTPBasicAuth
from flask import render_template
from flask import make_response
from flask import request
import os
from wasy import Wasy
from time import sleep
import json
import threading

auth = HTTPBasicAuth()
wpath = os.getenv('WASY_PATH', '/tmp/kobbi')
api_key = os.getenv('WASY_API', 'admin')

wasy = Wasy(wpath)
try:
    wasy.create()
except:
    None





app = Flask(__name__)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@auth.get_password
def get_password(username):
    if username == api_key:
        return 'pi'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


@app.route('/')
@auth.login_required
def index():
    return render_template("index.html",
                           title='Home')

@app.route('/view_clients')
@auth.login_required
def get_clients():
    clients = wasy.get_index_txt()
    return make_response(jsonify(clients), 200)

@app.route('/get_ca')
@auth.login_required
def get_ca():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        ca = wasy.get_ca(b64)
    return make_response(ca, 200)

@app.route('/get_server_key')
@auth.login_required
def get_server_key():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        key = wasy.get_server_key(b64)
    return make_response(key, 200)


@app.route('/get_server_crt')
@auth.login_required
def get_server_crt():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        crt = wasy.get_server_crt(b64)
    return make_response(crt, 200)

@app.route('/get_ta')
@auth.login_required
def get_ta():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        ta = wasy.get_ta(b64)
    return make_response(ta, 200)

@app.route('/get_dh')
@auth.login_required
def get_dh():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        dh = wasy.get_dh(b64)
    return make_response(dh, 200)


@app.route('/get_crl')
#@auth.login_required
def get_crl():
    if request.method == 'GET':
        b64 = request.args.get('b64')
        if b64 == None:
            b64=True
        crl = wasy.get_crl(b64)
    return make_response(crl, 200)


@app.route('/get_client')
@auth.login_required
def gget_client():
    if request.method == 'GET' and request.args.get('cn') != None and request.args.get('cn') != '':
        cn = request.args.get('cn')
        ovpn = wasy.make_ovpn(cn)
        return make_response(ovpn, 200)
    else:
        return make_response(jsonify({'result': 'Error missing data'}), 200)

@app.route('/add_client', methods=['POST', 'GET'])
@auth.login_required
def add_client():
    if request.method == 'GET' and request.args.get('cn') != None and request.args.get('cn') != '':
        cn = request.args.get('cn')
        client = wasy.create_cert_client(cn)
        print (cn)
        return make_response(jsonify({'result': client}), 200)
    else:
        return make_response(jsonify({'result': 'Error missing data'}), 200)

@app.route('/revoke_client', methods=['POST', 'GET'])
@auth.login_required
def revoke_client():
    if request.method == 'GET' and request.args.get('cn') != None and request.args.get('cn') != '':
        cn = request.args.get('cn')
        client = wasy.revokce_cert_client(cn)
        print (cn)
        return make_response(jsonify({'result': client}), 200)
    else:
        return make_response(jsonify({'result': 'Error missing data'}), 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5000')