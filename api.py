# import binascii
import pandas as pd
import requests
# import os
from werkzeug.utils import cached_property
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename, cached_property
from flask import Flask, request, flash, redirect, url_for
# import flask.scaffold
# flask.helpers._endpoint_from_view_func = flask.scaffold._endpoint_from_view_func
# import flask_restful
from flask_restful import abort, Api, Resource, reqparse
from apispec import APISpec
from marshmallow import Schema, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs
# from flask_restx import abort, Api, Resource
# from werkzeug.datastructures import FileStorage
import werkzeug
import json

# from flask_restplus import reqparse
# import flask_restplus as restplus

'''
file_upload = reqparse.RequestParser()
file_upload.add_argument('xls_file',
                         type=werkzeug.datastructures.FileStorage,
                         location='files',
                         required=True,
                         help='XLS file')
'''

app = Flask(__name__)
# UPLOAD_FOLDER = './files' # or later try only 'files'
# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'json'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

api = Api(app)
app.config.update({
    'APISPEC_SPEC': APISpec(
        title='Company Component',
        version='v1',
        plugins=[MarshmallowPlugin()],
        openapi_version='2.0.0',
        base_url='/',
        host='localhost:5002/',
        schemes='[http]'
    ),
    'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON
    'APISPEC_SWAGGER_UI_URL': '/swagger-ui/'  # URI to access UI of API Doc
})
docs = FlaskApiSpec(app)


##### SCHEMAS #####
# defining class with input descriptions for fetching the confirmation of data receipt related parameters
class ConfirmTransferParameters(Schema):
    uri = fields.String(required=True, description="URI of the data as received from the manager upon data registry.")
    hash = fields.String(required=True, description="Hash of the data sent by the sender to receiver.")
    sender_id = fields.String(required=True, description="ID of the sender of the data as received from the manager as response of notify data transfer.")
    signature_of_sender = fields.String(required=True, description="Signature of the sender as received from the manager as response of notify data transfer.")
    data_file_url = fields.String(required=True, description="URL of the actual data file for download.")
    # trip_file = fields.Dict(required=True, description= "Data to be transferred")


# defining class with input descriptions for register response of data receipt
class uploadTripFile(Schema):
    trip_data = fields.Dict(required=True, description="Data with trip details: [dict]")


# defining class with input descriptions for fetching input watermarked trajectory data for checking correlation
# class HashingSchema(Schema):
#    trip_data = fields.Dict(required=True, description="Data with watermarked trip details: [dict]")





##### START API ####
def run(host='0.0.0.0', port=5002, debug=True):
    app.run(host=host, port=port, debug=debug)


# This API is called when a data requester gets a data set from a data provider
# To finalize the data transfer the data requester confirms that he got the data
#
# Parameters:
# uri
# hash
# sender_id
# signature_of_sender
class Confirm_transfer_params(MethodResource, Resource):
    @doc(description='Parameters to be used for confirming the data transfer.',
         tags=['Parameters for Confirming Data Transfer'],
         responses={'200': {'description': 'Parameters sent successfully'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(ConfirmTransferParameters, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            data = {
                "uri": json_body['uri'],
                "hash": json_body['hash'],
                "sender_id": json_body['sender_id'],
                "signature_of_sender": json_body['signature_of_sender']
            }

            uniform_resource_identifier = json_body['uri']

            # call the api of module here to do confirm data transfer
            if (json_body['uri'] is None) or (json_body['hash'] is None) or (json_body['sender_id'] is None) or (
                    json_body['signature_of_sender'] is None):
                print('One of more mandatory input parameter missing')
                # prepare response in case one of the mandatory parameters data was not provided
                response_data = {"message": "Failure in sending the parameters data"}, 200
            else:
                response_data = {"message": "Confirm data input parameters sent successfully"}, 201

                # section to read the received data file and parse it or format it
                # download the data file from data_file_url field and then use it

                # section to hash the input data and then to verify it against the hash received
                # types: dict, tuple, list, int, float, ...
                # TODO: think about what to do if the file contains null, true, false values incompatible with json
                with open('files/trip_file.json', 'r') as f:
                    trips_data_dict = json.load(f)
                    #trips_data_dict = trips_data_dict[0]
                data = json.dumps(trips_data_dict, sort_keys=True)  # convert into string
                hash_data = str(hash(data)).encode() # get hash of string that gives an integer, then cast into string
                # and then encode into byte
                print('hash of the data is: ', hash_data)

                # in case the confirm transfer API needs to be called from this API itself then following to be executed
                headers = requests.utils.default_headers()
                user_agent = 'UserAgent' + str(json_body['sender_id'])
                headers.update(
                    {
                        'User-Agent': user_agent,
                        'Connection': 'Keep-Alive',
                    }
                )
                # call the API of module to confirm the data receipt
                headers = requests.utils.default_headers()
                headers.update(
                    {
                        'User-Agent': user_agent,
                        'Connection': 'Keep-Alive',
                    }
                )
                try:
                    r = requests.post(url='http://localhost:5001/confirm_transfer', json=data, headers=headers)
                    # or json_body can also be directly passed if we don't have to process the trip file to create hash
                    confirm_data_receipt_response = r.json()
                except Exception as ex:
                    print(ex)

                return response_data
        except Exception as e:
            return {"ERROR": str(e)}, 500


class UploadDemo(MethodResource, Resource):
    @doc(description='Data Provider can send to the receiver using this API.',
         tags=['Send Data'],
         responses={'200': {'description': 'Trajectory data watermarked successfully'},
                    '201': {'description': 'Incorrect format of input file'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(uploadTripFile, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            trip_data = json_body['trip_data']
            if len(trip_data) > 0:
                trip_id = str(trip_data['trip_id'])
                with open("files/"+trip_id+".json", 'w') as fp:
                    json.dump(json_body, fp)
                ret_msg = {"Message": "File contents sent successfully."}, 200
            else:
                ret_msg = {"Message": "File contents not in correct format."}, 201
            return ret_msg
        except Exception as e:
            return {"ERROR": str(e)}, 500


# Add Url Path
api.add_resource(Confirm_transfer_params, '/confirm_transfer_params')
api.add_resource(UploadDemo, '/upload')
# api.add_resource(Hash_Json, '/hash_json')

# Swagger Docs
docs.register(Confirm_transfer_params)
docs.register(UploadDemo)
# docs.register(Hash_Json)