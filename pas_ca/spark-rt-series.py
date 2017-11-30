#comando para iniciar: ../spark-1.5.2/bin/spark-submit --jars jars/spark-streaming-flume-assembly_2.10-1.5.2.jar acessos_redis_v2.py
import sys
import os
import datetime
import json
import random
from kairos import Timeseries
import redis
import numpy as np

os.environ["SPARK_HOME"] = "/home/marceloca/spark-1.5.2/"

sys.path.append("/home/marceloca/spark-1.5.2/python/")
sys.path.append("/home/marceloca/spark-1.5.2/python/lib/py4j-0.8.2.1-src.zip")

from pyspark.streaming.flume import FlumeUtils
from pyspark import SparkContext
from pyspark.streaming import StreamingContext


#Inicia conexao com servidor redis para salvar acessos
client = redis.Redis('10.125.8.253', 6379)

#Ajusta parametros serie temporal
t = Timeseries(client, type='histogram', read_func=int, intervals={
  'seconds':{
    'step':1,            # 1 second
    'steps':360,          # last 2 hours
  }
})

#Funcoes


###salva req com time
def salva_req_redis(req, time_stamp):
  t.insert('reqs', req, timestamp=int(time_stamp))


def salva_t_srv_queue_redis(t_srv_queue, time_stamp):
  t.insert('t_srv_queue', t_srv_queue, timestamp=int(time_stamp))


#funcao para converter data do haproxy para redis
def converte_data_redis(data):
  data_tmp=datetime.datetime.strptime(data, '%d/%b/%Y:%H:%M:%S.%f')
  return data_tmp.strftime('%s')

def salva_tempo_mais_recente(time_stamp):
  try:
    ultimo=client.get('tempo_mais_recente')
  except:
    ultimo = 0
  if int(ultimo) < int(time_stamp):
    client.set('tempo_mais_recente', int(time_stamp))


def salvaResultado(rdd):
    #coloca entradas no formato
    #(hora_da_req, quem_respondeu, tempo_de_resposta)
    linhas = rdd.map(lambda linha: (converte_data_redis(linha[6][1:len(linha[6])-1]), linha[8].split("/")[1], linha[9].split("/")[3]))

    for log in linhas.collect():
      salva_tempo_mais_recente(log[0])
      salva_req_redis(1, log[0])
      #Evitar salvar entradas com codigo http 500 com o Tr = -1
      if log[2] != -1:
        salva_t_srv_queue_redis(log[2], log[0])
      else:
        salva_t_srv_que_redis(50000, 0)

# Create a local StreamingContext with two working thread and batch interval of 1 second

sc = SparkContext("local[2]", "acessos")
#ssc = StreamingContext(sc, 20)
ssc = StreamingContext(sc, 5)
stream_flume_logs = FlumeUtils.createStream(ssc, "10.125.8.253", 44444)

#Pegar cada linha do log
linha_log = stream_flume_logs.map(lambda a: a[1]).filter(lambda a: "haproxy" in a)

#linha_log.pprint()

#words = linha_log.flatMap(lambda line: line.split(" "))
words = linha_log.map(lambda line: line.split())
#words.pprint()

#Processar dados e salvar no banco Influxdb
words.foreachRDD(salvaResultado)

ssc.start()             # Start the computation

