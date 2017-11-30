import numpy as np
import os, sys
from time import sleep
import redis
from kairos import Timeseries
from pid import *
#recupera volores do PID do Redis
rserver_dados_pid=redis.Redis('10.125.8.253', 6379, db=4)

def pega_setpoint():
  return float(rserver_dados_pid.get('setpoint'))

def salva_setpoint(setpoint):
  rserver_dados_pid.set('setpoint', setpoint)
  return 0


def salva_Kp(Kp):
  rserver_dados_pid.set('Kp', Kp)
  return 0


def salva_Ki(Ki):
  rserver_dados_pid.set('Ki', Ki)
  return 0

def salva_Kd(Kd):
  rserver_dados_pid.set('Kd', Kd)
  return 0

def pega_Kp():
  return float(rserver_dados_pid.get('Kp'))

def pega_Ki():
  return float(rserver_dados_pid.get('Ki'))

def pega_Kd():
  return float(rserver_dados_pid.get('Kd'))

def pega_setpoint():
  return float(rserver_dados_pid.get('setpoint'))

def atualiza_PID():
  Kp=pega_Kp()
  Ki=pega_Ki()
  Kd=pega_Kd()
  sys.stdout.write(str(Kp) + " " + str(Ki) + " " + str(Kd) +"\n")
  p.setKp(Kp)
  p.setKi(Ki)
  p.setKd(Kd)

#total_req_por_conteiner=18
tamanho_janela=200
#objetivo de tempo de resposta em ms
setpoint=80
rserver=redis.Redis('10.125.8.253')
#p=PID(0.2,0.1,0.01)
#Kp=0.05
#Ki=0
#Kd=0
##parametros metodo manual
#Kp=0.001
#Ki=0.000012
#Kd=0.096
###Parametros otimizados pelo twiddle 3 carga 4
Kp=0.00011
Ki=9e-05
Kd=9.11e-05

salva_Kp(Kp)
salva_Ki(Ki)
salva_Kd(Kd)
salva_setpoint(setpoint)
p=PID(Kp,Ki,Kd)
p.setPoint(setpoint)
min_pods=3
max_pods=30


#inicializa serie kairos-redis
t = Timeseries(rserver, type='histogram', read_func=int, intervals={
  'seconds':{
    'step':1,            # 60 seconds
    'steps':3600,          # last 2 hours
  }
})


#pega numero de instancias inicial

def num_instancias_inicial():
  os.system('kubectl get pods --namespace="rubis-ns" |grep Running| wc -l > /tmp/pods')
  n_pods_r=open('/tmp/pods')
  return int(n_pods_r.read()) - 1


def pega_tempo_mais_recente():
  return int(rserver.get('tempo_mais_recente'))


def pega_media_req_s_redis(inicio, fim):
  serie=t.series('reqs', 'seconds', start=inicio, end=fim, transform='sum')
  return np.mean(serie.values())

def pega_media_t_srv_queue_redis(inicio, fim):
  serie=t.series('t_srv_queue', 'seconds', start=inicio, end=fim, transform='mean')
  return np.mean(serie.values())


def dim_square_staffing(inicio, final):
  media_acessos=pega_media_req_s_redis(inicio, final)
  #print media_acessos
  dimensionamento = (media_acessos/total_req_por_conteiner) + 1.06*np.sqrt(media_acessos/total_req_por_conteiner)
  return int(dimensionamento)

def n_instancias_pid(diferenca_atual):
   saida_pid=-p.update(diferenca_atual)
   print saida_pid
   try:
     n_instancias_atual=rserver.get('ultimo_dimensionamento')
   except:
     print "n_instancias nao disponivel no servidor Redis"      
   resultado_pid= float(n_instancias_atual) + saida_pid
   if resultado_pid < min_pods:
     resultado_pid=min_pods
     #reincia PID
     #p=PID(Kp,Ki,Kd)
     p.setPoint(setpoint)
     
   if resultado_pid > max_pods:
     resultado_pid=max_pods
     #reinicia PID
     #p=PID(Kp,Ki,Kd)
     p.setPoint(setpoint)
    
   return resultado_pid

 
n_instancias_inicial=num_instancias_inicial()
rserver.set('ultimo_dimensionamento', n_instancias_inicial)

comando_zera_t_srv_queue="> /home/marceloca/analise_resultados/t_srv_queue_rubis/t_srv_queue"
os.system(comando_zera_t_srv_queue)


while True:
    try:
       #atualiza PID
       atualiza_PID()
       diferenca_atual=pega_media_t_srv_queue_redis(pega_tempo_mais_recente() - tamanho_janela*1, pega_tempo_mais_recente())
       print diferenca_atual
       comando_salva_t_srv_queue = 'echo ' + str(diferenca_atual) + '>> /home/marceloca/analise_resultados/t_srv_queue_rubis/t_srv_queue' 
       os.system(comando_salva_t_srv_queue)
       n_instancias=n_instancias_pid(diferenca_atual)
       print "n_instancias: " + str(n_instancias)
       rserver.set('ultimo_dimensionamento', n_instancias)
       sleep(10)
       comando="kubectl scale rc rubis --replicas=" + str(int(n_instancias)) + " --namespace='rubis-ns'"
       os.system(comando)

    except KeyboardInterrupt:
       print "Bye"
       sys.exit()
 
