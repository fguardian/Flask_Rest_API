# reto_rest_api
### Generación de End point para visualización de cultivos.

#### Paso a Paso:
Verifique que tiene todos los modulos de python:
- pip install flask
- pip install Shapely
- pip install flask_mysqldb
Si no puedes intallar flask_mysqldb ejecute con pip el archivo en la carpeta flask_mysqldb_problems_to_install:
- pip install "mysqlclient-1.4.6-cp38-cp38-win32.whl"
- pip install flask_mysqldb

Una ves instalados todos los mudulos de python:
- Ejecutar Server y iniciar la APP: Para inicar el Script tendras que ejecutar el Script "app.py" (python app.py)
- Al ejecutar el Script te devolvera una ruta de un servidor local que se ha creado al cual deberas ingresar. 
- Ingresar el ID en el formulario y presionamos en el boton "Obtener Informacion de Cultivos"

- Si el User existe dentro de la base de datos se te redireccionara a un end point "*/informacion_cultivos" que te proporcionara un JSON
  con toda la informacion de los cultivos que exista para tu user.
  
