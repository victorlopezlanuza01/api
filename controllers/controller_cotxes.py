import json, jwt
import paho.mqtt.client as mqtt
from flask import jsonify, request

import datetime
from datetime import timedelta

from models.models import *
from utils.utils import checktoken

import logging
logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')

OK = 'ok'
INTERNAL = 'internal'

RES_OK  = { 'value': "ok" }
FAILED  = { 'value': "failed" }

CAR_START_ROUTE = 1

def cars_full_info():
    if is_local == 1:
        return jsonify({'result':'error, funcio no disponible al edge'})
    data = request.get_json()
    value = checktoken(data['session_token'])
    response = {'value': value['valid']}
    
    if value['valid'] == 'ok':
        coches = camions.find()
        res=([{
            'id_car': doc['id_car'],
            'id_route': doc['id_route'],
            'license_plate': doc['license_plate'],
            'battery': doc['battery'],
            'status_text': doc['status'],
            'status': doc['status_num'],
            'autonomy': doc['autonomy'],
            'capacity': doc['capacity'],
            'last_maintenance_date': doc['last_maintenance_date'],
            'packages': doc['packages'],
            'beehive': doc['beehive'],
            'location_in ': doc['location_in'],
            'location_act': doc['location_act'],
            'location_end': doc['location_end'],
    }for doc in coches])
        return jsonify({'result':'ok','cars':res})
    else:
        return jsonify(response)

def car_pos_info():
    if is_local == 1:
        return jsonify({'result':'error, funcio no disponible al edge'})
    data = request.get_json()
    value = checktoken(data['session_token'])
    response = {'result': value['valid']}

    if response['result'] == 'ok':
        coches = camions.find()
        return jsonify(response, [{
            'id_car': doc['id_car'],
            'latitude ': doc['location_act']['latitude'],
            'longitude': doc['location_act']['longitude'],
        }for doc in coches])

    return jsonify(response)

def list_available_cars():
    if is_local == 1:
        return jsonify({'result':'error, funcio no disponible al edge'})
    data = request.get_json()
    value = checktoken(data['session_token'])
    response = {'result': value['valid']}

    if value['valid'] =='ok':
        coches = camions.find({'status':"waits"})
        response['cars'] = [{
            'id_car': doc['id_car'],
            'status': doc['status'],
            'autonomy': doc['autonomy'],
            'capacity': doc['capacity']
        }for doc in coches]
    return jsonify(response)

def prova_list_available_cars():
    if is_local == 1:
        return jsonify({'result':'error, funcio no disponible al edge'})
    response = {'value': 'cloduy'}
    coches = camions.find({'status':"waits"})
    return jsonify(response, [{
        'id_car': doc['id_car'],
        'latitude ': doc['location_act']['latitude'],
        'longitude': doc['location_act']['longitude'],
    }for doc in coches])




def list_orders_to_send_cars():
    
    if is_local == 1:
        return jsonify({'result':'error, funcio no disponible al edge'})
    
    data = request.get_json()
    value = checktoken(data['session_token'])
    if value['valid'] =='ok':
        orderss = orders.find({'state':"ordered"})
        ordersss = []
        for doc in orderss:
            # colmena_random_cursor = colmenas.aggregate([{ "$sample": { "size": 1 } }])
            # colmena_random = next(colmena_random_cursor, None)
            # colmena_random = colmenas.find_one()

            # De momento ponemos esta 
            colmena_random = colmenas.find_one({
                'zip_code' : '08880'
            })
            ordersss.append({
                'order_identifier': doc['order_identifier'],
                'beehive_coords_destiny': {
                    'id_beehive'    :   colmena_random['id_beehive'],
                    'latitude'      :   colmena_random['location_end']['latitude'],
                    'longitude'     :   colmena_random['location_end']['longitude']
                },
                'medicine_list': [{
                    'medicine_identifier': medicine
                } for medicine in doc['meds_list']],
                'date'  : doc['date'],
                'state' : doc['state'],
            })

        return jsonify({
            'result': value['valid'],
            'orders': ordersss})
        # return jsonify({
        #     'result': value['valid'],
        #     'orders': [{
        #         'order_identifier': doc['order_identifier'],
        #         'beehive_destiny': {
                        # doc['colmena']['location_end']mirar api calls A3 i completar con la colmena quando neste en basde de datos
        #         'medicine_list': [{
        #             'medicine_identifier': medicine
        #         } for medicine in doc['meds_list']],
        #         'date': doc['date'],
        #         'state': doc['state'],
        # }for doc in orderss]
        # })
    else:
        response = {'result': value['valid']}
    return jsonify(response)


def send_order_cars():
    
    data = request.get_json()
    value = checktoken(data['session_token'])
    
    if value['valid'] != OK or value['type'] != INTERNAL:
        return jsonify(FAILED)
    
    for car in data['assignations']:

        id_car      = car['id_car']
        id_beehive  = car['id_beehive']
        id_route    = car['route']['id_route']
        coordinates = routes.find_one({'id_route' : id_route})

        packages = []        
        [ packages.append({ 'order_identifier' : str(order['order_identifier'])}) for order in car['cargo'] ]

        update_fields = { 
            'id_route'  : id_route,
            'beehive'   : id_beehive,
            'packages'  : packages
        }
        result = camions.update_one(
            {'id_car'   : id_car }, 
            {'$set'     : update_fields }
        )

        if result.modified_count > 0:
            send_car(id_car, coordinates['coordinates'])

        else:
            logging.info("CARS | El documento no se actualizó. Puede que no se encontrara el id_car especificado.")
            return jsonify(FAILED), 404

    return jsonify(RES_OK)



def send_car(id_car, route):
   
    client = mqtt.Client()
    client.connect("mosquitto", 1883, 60)

    msg = {    
        "id_car"    :   id_car,
        "order"     :   CAR_START_ROUTE,
        "route"     :   str(route)
    }
    message = json.dumps(msg)
    logging.info(message)

    client.publish("PTIN2023/CAR/STARTROUTE", message)
    client.disconnect()
