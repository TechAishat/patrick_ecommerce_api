import pymysql
pymysql.install_as_MySQLdb()

try:
    connection = pymysql.connect(
        host='Aishat.mysql.pythonanywhere-services.com',
        user='Aishat',
        password='Cavanni122#',
        database='Aishat$default',
        port=3306
    )
    print('✅ Successfully connected to the database!')
    connection.close()
except Exception as e:
    print(f'❌ Error: {e}')