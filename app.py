from flask import Flask, render_template, request, redirect, url_for
from config import config, CropColumns,DeviceColumns
from flask_mysqldb import MySQL
import json
import datetime
from shapely.geometry import Polygon,Point
import time
app = Flask(__name__)

# MY SQL CONNECTION
app.config['MYSQL_HOST']      = config['DataBaseConfig']['MYSQL_HOST']
app.config['MYSQL_PORT']      =  config['DataBaseConfig']['MYSQL_PORT']
app.config['MYSQL_USER']      = config['DataBaseConfig']['MYSQL_USER']
app.config['MYSQL_PASSWORD']  = config['DataBaseConfig']['MYSQL_PASSWORD']
app.config['MYSQL_DB']        = config['DataBaseConfig']['MYSQL_DB']
MySql = MySQL(app)
app.secret_key = ''

@app.route('/') 
def Index():
    return render_template('index.html')

@app.route('/informacion_cultivos', methods=['POST'])
def GetInfo():
    if request.method == 'POST':
        Id = request.form['id']
        Cur = MySql.connection.cursor()
        Cur.execute('SELECT name, email, users_id FROM users WHERE id = %s'%str(Id))
        User = Cur.fetchall()[0]
        UserName = User[0]
        UserEmail = User[1]
        UsersId = User[2]
        if User:
            if UsersId != None:
                Data = GetData(MySql,UsersId)
                JsonData = json.dumps(Data.Data , indent = 6)
            else:
                return "Biencenido %s, no hay cultivos" % str(UserName)
            return "<p> %s </p>" % str("<pre>"+JsonData+"</pre>").replace('\n','<br>').replace('\t','   ')
        else:
            return "El Usuario con ID:  No existe" % Id

def WebPageNotFound (Error):
    return "<h1>La pagina buscada no existe</h1>"
def WebPageIvalidGet (Error):
    return redirect(url_for('Index'))


class GetData (object):
    def __init__(self,MySql,UserId):
        self.CropsId = []
        self.UserCropsInfo = {}
        self.CropFormat= {}
        self.DevicesId = []
        self.UserDeviceInfo = {}
        self.DeviceDataType = {}
        self.SensoresData = {}
        self.SensoresId = {}
        self.DataMergeId = {}
        self.CropPolyLine = {}
        self.Data = {'data':[]}

        self.GetCrops(MySql,UserId)
        if len(self.UserCropsInfo.keys()) > 0:
            self.GetDevices(MySql,UserId)
            if len(self.UserDeviceInfo.keys()) > 0:
                self.GetPositionCrops()
                self.MergeCropsAndDevice()
        self.AddDeviceDataToCrop()

    def GetCrops (self,MySql,UserId):
        Cur = MySql.connection.cursor()
        Cur.execute('SELECT cultivos_id FROM users_has_cultivos WHERE users_id = %s'%str(UserId))
        UserCropsInfo = Cur.fetchall()
        SqlWhere = 'WHERE '
        for crop in UserCropsInfo:
            CropId = crop[0]
            if not CropId in self.CropsId :
                self.CropsId.append(CropId)
                SqlWhere = SqlWhere + 'id = %s OR '%str(CropId)
        Cur = MySql.connection.cursor()
        Cur.execute('SELECT %s FROM  cultivos %s'%(CropColumns,str(SqlWhere[:-3])))
        CropsData= Cur.fetchall()
        for crop in CropsData:
            CropId = crop[0]
            self.UserCropsInfo[CropId] = crop
            self.CropFormat[CropId] = self.JsonFormatGropStart(crop)

    def GetDevices (self,MySql,UserId):
        # Buscamos en la tabla users_has_biodispositivos los Id de los biodispositivos
        Cur = MySql.connection.cursor()
        Cur.execute('SELECT bio_dispositivos_id FROM users_has_biodispositivos WHERE users_id = %s'%str(UserId))
        UserDeviceInfo = Cur.fetchall()
        if UserDeviceInfo:
            SqlWhere = 'WHERE '
            for device in UserDeviceInfo:
                DeviceId = device[0]
                if not DeviceId in self.DevicesId:
                    self.DevicesId.append(DeviceId)
                    SqlWhere = SqlWhere + 'id = %s OR '%str(DeviceId)

            # Buscamos las filas de la informacion de los biodispositivos
            Cur = MySql.connection.cursor()
            Cur.execute('SELECT %s FROM  bio_dispositivos %s'%(DeviceColumns,str(SqlWhere[:-3])))
            DeviceData = Cur.fetchall()
            DeviceMergeType = {}
            TypesId = []
            self.DevicesId = []
            SqlWhereType = 'WHERE '
            SqlWhereSensor = 'WHERE '
            if DeviceData:
                for device in DeviceData:
                    activo = device[-2]
                    if activo == 1:
                        DeviceId = device[0]
                        self.UserDeviceInfo[DeviceId] = device
                        if not DeviceId in self.DevicesId:
                            self.DevicesId.append(DeviceId)
                            SqlWhereSensor = SqlWhereSensor + 'bio_dispositivos_id = %s OR '%str(DeviceId)
                            if not device[3] in DeviceMergeType.keys():
                                DeviceMergeType[device[3]] = [device[0]]
                                SqlWhereType = SqlWhereType + 'id = %s OR '%str(device[3])
                            else:
                                DeviceMergeType[device[3]].append(device[0])
                print (DeviceMergeType)
                # Obtener Informacion de tabla tipo_dispositivos para cada Device
                Cur = MySql.connection.cursor()
                Cur.execute('SELECT id,tipo,modulos FROM tipo_biodispositivos %s'%(str(SqlWhereType[:-3])))
                DeviceDataType = Cur.fetchall()
                if DeviceDataType:
                    for DeviceType in DeviceDataType:
                        for deviceId in DeviceMergeType[DeviceType[0]]:
                            self.DeviceDataType[deviceId] = DeviceType

                # Obtenemos Informacion de los sensores en los biodispositivos
                Cur = MySql.connection.cursor()
                Cur.execute('SELECT bio_dispositivos_id,sensores_id,created_at FROM sensores_has_bio_dispositivos  %s '%(str(SqlWhereSensor[:-3])))
                SensoresData = Cur.fetchall()
                if SensoresData:
                    SqlWhereSensorLast = 'WHERE '
                    sensorDataInfo = {}
                    for sensor in SensoresData:
                        if not sensor[1] in self.SensoresId.keys():
                            self.SensoresId[sensor[1]] = sensor[1]
                            if not sensor[2] == None:
                                SqlWhereSensorLast = SqlWhereSensorLast + 'sensores_id = %s OR '%str(sensor[1])
                    start=time.time()
                    # Obtenemos informacion de tabla sensores_log
                    Cur = MySql.connection.cursor()
                    Cur.execute('SELECT sensores_id,updated_at,created_at FROM sensores_log %s'%(str(SqlWhereSensorLast[:-3])))
                    SensoresLastData = Cur.fetchall()
                    LastDataInfo = {}
                    if SensoresLastData:
                        for LastData in SensoresLastData:
                            if LastData[2] != None:
                                last = LastData [1] if LastData [1] != None else LastData [2]
                                if LastData[0] in LastDataInfo.keys() :
                                    if last > LastDataInfo[LastData[0]]:
                                        LastDataInfo[LastData[0]] = last
                                else:
                                    LastDataInfo[LastData[0]] = last
                    for sensor in SensoresData:
                        if not sensor[1] in LastDataInfo.keys():
                            LastDataInfo[sensor[1]] = None
                        if sensor[0] in self.SensoresData.keys():
                            self.SensoresData[sensor[0]].append([sensor[1],LastDataInfo[sensor[1]]])
                        else:
                            self.SensoresData[sensor[0]] = [[sensor[1],LastDataInfo[sensor[1]]]]
    
    def GetPositionCrops(self):
        for cropkey in self.UserCropsInfo.keys():
            crop = self.UserCropsInfo[cropkey]
            Polylines = crop[-1][1:-1][1:-1]
            CropId = crop[0]
            self.CropPolyLine[CropId] = []
            for points in Polylines.split('],['):
                point = points.split(',')
                x = float(point[0])
                y = float(point[1])
                self.CropPolyLine[CropId].append([float(point[0]),float(point[1])])

    def MergeCropsAndDevice(self):
        array = []
        for CropId in self.CropsId:
            self.DataMergeId[CropId] = []
            Poly = Polygon(self.CropPolyLine[CropId])
            is_position_merged = {}
            for DeviceId in self.DevicesId:
                if DeviceId in self.UserDeviceInfo.keys():
                    is_position_merged[DeviceId] = False
                    activo = self.UserDeviceInfo[DeviceId][-2]
                    if activo == 1:
                        self.DataMergeId[CropId].append(DeviceId)
                        self.CropFormat[CropId]

                    #if self.UserDeviceInfo[DeviceId][-1] != None and self.UserDeviceInfo[DeviceId][-1] != '[]':
                    #    position = self.UserDeviceInfo[DeviceId][-1][1:-1][1:-1] if self.UserDeviceInfo[DeviceId][-1][:2] == '[[' else self.UserDeviceInfo[DeviceId][-1][1:-1]
                    #    x,y = position.split(',')
                    #    IsDeviceInCrop = Poly.contains(Point(float(x),float(y)))
                    #    if IsDeviceInCrop:
                    #        self.DataMergeId[CropId].append(DeviceId)
                    #        self.CropFormat[CropId]
                    #else:
                    #    self.DataMergeId[CropId].append(DeviceId)
            
    def JsonFormatGropStart(self,crop):
        return {
            'nombre'                : crop[1],
            'ciclo_cultivo_id'      : crop[2],
            'ambiente_cultivo_id'   : crop[3],
            'fecha_inicio'          : str(crop[4]),
            'fecha_final'           : str(crop[5]),
            'clave_cultivo'         : crop[6],
            'creador_id'            : crop[7],
            'id'                    : crop[0],
            'predios_id'            : crop[8],
            'tipos_cultivo_id'      : crop[9],
            "devices"               : []
        }

    def AddDeviceDataToCrop (self):
        change = 0
        for CropId in self.CropsId:
            if CropId in self.DataMergeId.keys():
                for DeviceId in self.DataMergeId[CropId]:
                    Device = self.UserDeviceInfo[DeviceId]
                    if DeviceId in self.DeviceDataType.keys():
                        DeviceType = self.DeviceDataType[DeviceId]
                    else:
                        DeviceType = None
                    if  DeviceId in self.SensoresData.keys():
                        DeviceSensor = self.JsonLastLogFormat(self.SensoresData[DeviceId],DeviceId)
                    else:
                        DeviceSensor = None
                    self.CropFormat[CropId]['devices'].append(self.JsonDeviceFormat(Device,DeviceType,DeviceSensor,CropId))
            self.Data['data'].append (self.CropFormat[CropId])

    def JsonDeviceFormat(self,DeviceInfo,DeviceTypeInfo,DeviceSensorInfo,CropId):
        if DeviceTypeInfo == None:
            DeviceTypeInfo = [None,None,None]
        data = {
            'nombre'                : DeviceInfo[1],
            'clave'                 : DeviceInfo[2],
            'id'                    : DeviceInfo[0],
            'tipo_dispositivo_id'   : DeviceInfo[3],
            'pivot'                 : {
                                        'bio_dispositivos_id' : DeviceInfo[0],
                                        'cultivos_id'         : CropId
                                    },
            'last_log'              : DeviceSensorInfo,
            'device_type'           : {
                                        'id'        : DeviceTypeInfo[0],
                                        'nombre'    : DeviceTypeInfo[1],
                                        'modulos'   : DeviceTypeInfo[2]
                                    }
        }
        """
        if DeviceSensorInfo != None:
            for Id, Time in DeviceSensorInfo:
                data['last_log'].append(
                    {
                        'value_datetime' : str(Time),
                        'pivot'          : {
                                            'bio_dispositivos_id' : DeviceInfo[0],
                                            'sensores_id'         : Id
                                        }
                    }
                )"""
        return data
    def JsonLastLogFormat(self,DeviceSensorInfo,DeviceId):
        LastLog = []
        for Id, Time in DeviceSensorInfo:
                LastLog.append(
                    {
                        'value_datetime' : str(Time),
                        'pivot'          : {
                                            'bio_dispositivos_id' : DeviceId,
                                            'sensores_id'         : Id
                                        }
                    }
                )
        return LastLog 
if __name__ == '__main__':
    app.register_error_handler(404,WebPageNotFound)
    app.register_error_handler(405,WebPageIvalidGet)
    app.run(port = 3000, debug = True)
