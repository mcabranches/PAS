import numpy as np
import os, sys
import datetime
from time import sleep
import redis
from kairos import Timeseries
from pid import *

rserver_dados_pid=redis.Redis('10.125.8.253', 6379, db=4)
rserver_timeseries=redis.Redis('10.125.8.253')
#inicializa serie kairos-redis
t = Timeseries(rserver_timeseries, type='histogram', read_func=int, intervals={
  'seconds':{
    'step':1,            # 60 seconds
    'steps':3600,          # last 2 hours
  }
})


tamanho_janela=200



def pega_setpoint():
  return float(rserver_dados_pid.get('setpoint'))

def salva_Kp(Kp):
  rserver_dados_pid.set('Kp', float(Kp))
  return 0


def salva_Ki(Ki):
  rserver_dados_pid.set('Ki', float(Ki))
  return 0

def salva_Kd(Kd):
  rserver_dados_pid.set('Kd', float(Kd))
  return 0

def pega_Kp():
  return float(rserver_dados_pid.get('Kp'))

def pega_Ki():
  return float(rserver_dados_pid.get('Ki'))

def pega_Kd():
  return float(rserver_dados_pid.get('Kd'))

def pega_setpoint():
  return float(rserver_dados_pid.get('setpoint'))

def pega_time_stamp():
  hora=datetime.datetime.now()
  return int(hora.strftime('%s'))

def pega_serie_redis(inicio, fim):
  serie=t.series('t_srv_queue', 'seconds', start=inicio, end=fim, transform='mean')
  return serie.values()

def calcula_erro_rms(serie, setpoint):
  erro_rms=0
#  print serie
  for i in serie:
    erro_rms += np.sqrt(np.power((i - setpoint), 2))
  return np.mean(erro_rms)

def verifica_erro_rms_diminuiu(erro_rms_atual, erro_rms_anterior):
  diminuiu = False
  print "erro anterior:" + str(erro_rms_anterior)
  print "erro atual:" + str(erro_rms_atual)
  if erro_rms_atual < erro_rms_anterior:
    diminuiu = True
    print "Diminuiu"
  return diminuiu


def calcula_erro(tamanho_janela):
  erros=[]
  for i in range(2000):
    serie=pega_serie_redis(pega_time_stamp() - tamanho_janela, pega_time_stamp())
    erro_rms_atual=calcula_erro_rms(serie, setpoint)
    erros.append(erro_rms_atual)
    sleep(1)
  print erros
  erro_medio=np.mean(erros)
  print erro_medio
  return erro_medio

#def calcula_erro(tamanho_janela):
#  serie=pega_serie_redis(pega_time_stamp() - janela, pega_time_stamp())
#  erro_rms_atual=calcula_erro_rms(serie, setpoint)
#  print "erro_rms_atual: " + str(erro_rms_atual)
#  return erro_rms_atual


def atualiza_parametros(i,p):
  print "atualiza_parametros"
  if i == 0:
    salva_Kp(p[0])
    print "Kp: " + str(pega_Kp())
  if i == 1:
    salva_Ki(p[1])
    print "Ki: " + str(pega_Ki())
  if i == 2:
    salva_Kd(p[2] )
    print "Kd: " + str(pega_Kd())
  #sleep(200)

#twiddle

#choose an initialization parameter vector

setpoint=pega_setpoint()
p = [pega_Kp(), pega_Ki(), pega_Kp()]
# Define potential changes
dp = [0.00001, 0.000001, 0.00001]
# Calculate the error
#best_err = calcula_erro(tamanho_janela)
best_err = 50000

threshold = 0.000001

#sleep(1000)
while sum(dp) > threshold:
    
    for i in range(len(p)):
        print str(p[i])
        print str(dp[i])
        p[i] += dp[i]
        print str(p[i])
        atualiza_parametros(i,p)       
        err = calcula_erro(tamanho_janela)
        if err < best_err:  # There was some improvement
            print "Melhorou"
            best_err = err
            dp[i] *= 1.1

        else:  # There was no improvement
            p[i] -= 2*dp[i]  # Go into the other direction
            atualiza_parametros(i,p)
            err = calcula_erro(tamanho_janela)

            if err < best_err:  # There was an improvement
                print "Melhorou"
                best_err = err
                dp[i] *= 1.1
            else:  # There was no improvement
                p[i] += dp[i]
                atualiza_parametros(i,p)
                # As there was no improvement, the step size in either
                # direction, the step size might simply be too big.
                dp[i] *= 0.9

#        if i == 0:
#          salva_Kp(p[0])
#          print "Kp: " + str(pega_Kp()) 
#        if i == 1:        
#          salva_Ki(p[1])
#          print "Ki: " + str(pega_Ki())
#        if i == 2:  
#          salva_Kd(p[2] )
#          print "Kd: " + str(pega_Kd())
        
