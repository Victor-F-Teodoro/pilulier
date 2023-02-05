## PARTIE 1 - Importation des bibliothèques et modules nécessaires au fonctionnement du code

# le module GPIO de la bibliothèque possède les fonctions qui relient
# la RaspBerry Pi aux composants électroniques.
from RPi import GPIO

# 'time' nous permet de faire le code attendre une quantité donnée de secondes
# avant de continuer l'exécution
from time import sleep
import time

# 'request' sert à faire des requêtes http aux APIs
import requests

# datetime permet la transformation de Strings en Dates
# Les Dates peuvent être sommées ou sous-traitées
from datetime import datetime, date
import numpy as np
import os


## PARTIE 2 - Création des classes et fonctions utilisées par le système


def shutdown_time(time):
    """
    Permet d'éteindre la RaspBerry Pi de façon remote
        INPUTS : None
    OUTPUTS : None
    """
    sleep(30)
    os.system("/sbin/shutdown now")


class ServerCommunication:
    url = "http://172.21.4.210/api/"
    get_adress = "get/alarms/"
    edit_adress = "edit/alarms/"

    def get(self):
        r = requests.get(ServerCommunication.url+ServerCommunication.get_adress)
        return r

    def put(self, id, slot, time, name):
        mydata = {
            "mode": slot,
            "time": time,
            "name": name
            }
        r = requests.put(ServerCommunication.url+ServerCommunication.edit_adress+id+"/", data=mydata)
        print(r.content)
        return r

    def delete(self, id):
        mydata = {}
        r = requests.delete(ServerCommunication.url+ServerCommunication.edit_adress+id+"/", data=mydata)


class Motor():
    """
    L'objet 'Motor' est responsable pour le fonctionnement du système. Il contrôle le fonctionnement du 
    moteur, des capteurs infrarouges, du klaxon et prend les Outputs du bouton. 
    """
    def __init__(self):
        """
        Pour initialiser Moteur, on a besoin d'attribuer une ou plusieurs portes GPIO à chaque composant
        électronique du système. Cela est fait avec la fonction 'setmode' du module GPIO.       
        """

        # définition de la convention de numéro de porte utilisée. Pour ce projet, nous allons utiliser BOARD.
        GPIO.setmode(GPIO.BOARD)

        # capteurs infrarouges occuperons les portes 15 et 19 de la RaspBerry Pi
        self.ext_sensor = 15
        self.int_sensor = 19

        GPIO.setup(self.ext_sensor, GPIO.IN)
        GPIO.setup(self.int_sensor, GPIO.IN)

        # boutton
        self.button = 18
        
        GPIO.setup(self.button, GPIO.IN)
        
        # le moteur a besoin de quatre portes
        self.control_pin = [5, 23, 11, 13]
        
        for pin in self.control_pin:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)
        
        # klaxon
        self.buzzer = 21
        GPIO.setup(self.buzzer,GPIO.OUT)
        
        # création d'une instance de la classe ServerCommunication pour faire des requêtes http
        self.s = ServerCommunication()

    def check_ext_sensor(self):
        """
        Vérifier si le capteur extérieur capte un objet dans son champ d'action.

        Args:
            None

        Retourne :
            boolean : True si le capteur capte un objet et False le cas contraire.
        """
        try:
            if not GPIO.input(self.ext_sensor):
                return True
            else:
                return False
        except:
            GPIO.cleanup()
    

    def check_int_sensor(self):
        """
        Vérifier si le capteur intérieur capte un objet dans son champ d'action.

        Args:
            None

        Retourne :
            boolean : True si le capteur capte un objet et False le cas contraire.
        """
        while True:
            try:
                if not GPIO.input(self.int_sensor):
                    print("True")
                    return True
                else:
                    print("False")
                    return False
            except:
                GPIO.cleanup()


    def spin_motor(self, nb_turns):
        """
        Fait le moteur tourner jusqu'à ce que l'ouverture du couvercle ait passé au-dessus
        d'un nombre n de compartiments  
        Args:
            nb_turns (int) : nombre de n de compartiment que l'ouverture du couvercle passera 
            dessus d'un compartiment avant d'arrêter le moteur

        Returns:
            None
        """
        # liste avec les différents pas du moteur
        seq = [ [1, 0, 0, 0],
                [1, 1, 0, 0],
                [0, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
                [1, 0, 0, 1] ]

        flag_motor = True
        turns = 0
        while turns < nb_turns:

            # la condition flag_motor == True est utilisée pour que 'turn' n'augmente qu'une
            # seule fois à chaque passage de l'ouverture du couvercle au-dessous d'un compartiment
            if flag_motor:

                # envoy d'un signal au moteur pour qu'il puisse tourner au prochain pas    
                for pin_1, pin_2, pin_3, pin_4 in seq:
                    GPIO.output(self.control_pin[0], pin_1)
                    GPIO.output(self.control_pin[1], pin_2)
                    GPIO.output(self.control_pin[2], pin_3)
                    GPIO.output(self.control_pin[3], pin_4)
                    sleep(0.005)
                status = self.check_ext_sensor()
                if status == False:
                    turns += 1
                    flag_motor = False

            elif flag_motor == False:
                for pin_1, pin_2, pin_3, pin_4 in seq:
                    GPIO.output(self.control_pin[0], pin_1)
                    GPIO.output(self.control_pin[1], pin_2)
                    GPIO.output(self.control_pin[2], pin_3)
                    GPIO.output(self.control_pin[3], pin_4)
                    sleep(0.005)
                status = self.check_ext_sensor()
                if status:
                    flag_motor = True 


    def rot_origin(self):
        """
        Fait tourner le moteur jusqu'à ce que l'origine soit trouvée, sonne le klaxon
        et identifie si l'utilisateur a appuyé sur le bouton.   
        Args:
            None    
        Returns
            btn_pressed (boolean) : True si l'utilisateur a appuyé, False le cas contraire

        """
        seq = [ [1, 0, 0, 0],
                [1, 1, 0, 0],
                [0, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
                [1, 0, 0, 1] ]

        turns = 0
        status = True
        while status: 
            for pin_1, pin_2, pin_3, pin_4 in seq:
                GPIO.output(self.control_pin[0], pin_1)
                GPIO.output(self.control_pin[1], pin_2)
                GPIO.output(self.control_pin[2], pin_3)
                GPIO.output(self.control_pin[3], pin_4)
                sleep(0.005)
            status = self.check_int_sensor()
        print("origin found")
        i= 0
        btn_pressed = False
        beep_start = time.time()
        now = time.time()
        # on donne 12 secondes pour que l'utilisateur puisse appuyer sur
        # lu bouton
        while (now - beep_start) < 12:
            # alors qu'il n'appuye pas, le klaxon reste activé
            if GPIO.input(self.button) == GPIO.HIGH:
                GPIO.output(self.buzzer,GPIO.HIGH)
                print ("Beep")
                sleep(0.1) # Delay in seconds
                GPIO.output(self.buzzer,GPIO.LOW)
                print ("No Beep")
                sleep(0.1)
                now = time.time()
            else: break

        GPIO.output(self.buzzer,GPIO.LOW)

        if not GPIO.input(self.button) == GPIO.HIGH:
            btn_pressed = True
            print("button pressed")

        return btn_pressed  
    def spin_motor_alarm(self, nb):
        """
        Cette fonction relie les deux fonctions précédentes, permettant
        trouver l'origine, sonner le klaxon, attendre jusqu'à ce que l'utilisateur appuyé sur
        le bouton et tourner le moteur jusqu'à ce que l'ouverture du couvercle soit
        bien dessus le bon compartiment de médicaments  
        Args :
            nb (int) : numéro de la fente ou les médicaments se trouvent    
        Retourne :
            None
        """ 
        motor.rot_origin()
        sleep(0.5)
        self.status = True
        motor.spin_motor(nb)
        i= 0
        while i < 5:
            GPIO.output(self.buzzer,GPIO.HIGH)
            print ("Beep")
            sleep(0.1) # Delay in seconds
            GPIO.output(self.buzzer,GPIO.LOW)
            print ("No Beep")
            sleep(0.1)
            i = i+1
        GPIO.output(self.buzzer,GPIO.LOW)
    
    def get_next_schedule_compart(self, curr_time):
        """
        Trouve le prochain créneau et retourne ses caractéristiques 
        Args :
            curr_time (datetime) : l'heure actuelle

        Retourne :
            time (datetime) : l'heure du prochain créneau

            compartiment (int) : le numéro du compartiment où sont les médicaments qui seront dispensés

            id (str) : l'id du créneau dans la base de données du pilulier

            orig_time (str) : heure et date du créneau, dans le format "%Y-%m-%dT%H:%M:%SZ", ce qui 
            correspond, respectivement, à : Année, Mois, Jour, Heure, Minute, Seconde, Timezone 
        """
        dic_ids = {}
        dic_times = {}
        dic_compart = {}
        dic_orig_time = {}  
        # prendre les créneaux stockés dans la base de données du pilulier
        r = self.s.get()
        lt = eval(r.content.replace(b"false",b"False"))
        print(lt)

        for i in range(len(lt)):
            # trasformer le temps original dans un format 'datetime'
            time = datetime.strptime(lt[i]["time"], "%Y-%m-%dT%H:%M:%SZ").time()
            print(time)
            # on prend en compte que les créneaux avec un horaire qui vient après l'heure actuelle
            if time > current_time:
                dic_times[lt[i]["id"]] = time
                dic_orig_time[lt[i]["id"]] = lt[i]["time"]
            else: continue
            dic_ids[lt[i]["id"]] = lt[i]["id"]
            dic_compart[lt[i]["id"]] = lt[i]["mode"]

        # si la liste de créneaux valides n'est pas vide, on retourne
        # time, compartiment, id et orig_time. Sinon, on retourne juste None
        if len(list(dic_times.values())) > 0:
            val = str(min(dic_times.values()))
            val = datetime.strptime(val, "%H:%M:%S").time()
            index = list(dic_times.values()).index(val)
            compartiment = list(dic_compart.values())[index]
            time = list(dic_times.values())[index]
            orig_time = list(dic_orig_time.values())[index]
            id = list(dic_ids.values())[index]
            return time, compartiment, id, orig_time

        else: return None, None, None, None
    

    def time_difference(self, end_time, start_time):
        """
        Calcule la différence en minutes entre deux horaires    
        Args :
            end_time (datetime) : l'heure du prochain créneau   
            start_time (datetime) : l'heure actuelle

        Retourne :
            diff (int) : différence en minutes entre les deux horaires
        """
        diff = datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
        diff = str(diff)
        diff = datetime.strptime(diff, "%H:%M:%S").hour*60 + datetime.strptime(diff, "%H:%M:%S").minute
        return diff


## Partie 3 - Création de la boucle de fonctionnement

# création d'un log pour pouvoir debugger. Lorsque la Raspberry Pi est avec Crontab activé,
# les seuls messages reçus sont à travers de logs. Pour plus de détails, regarder le rapport
# final dans la section #TODO ajouter section   
with open("/home/pi/Desktop/startup.txt","a") as f:
    f.write("boot log: [" + str(datetime.now()) + "] system booted\n")

# création d'une instance de la classe Mortor
motor = Motor()

try:
    while True:
    
        # on fait une requête http au API WorldTime pour obtenir l'heure actuelle  
        r = requests.get('http://worldtimeapi.org/api/timezone/Europe/Paris')
        json = r.json()
        current_time = json['datetime']
        current_time = str(current_time)[:19]
        current_time = datetime.strptime(current_time, "%Y-%m-%dT%H:%M:%S").time()  
        # utilisation de 'get_next_schedule_compart' pour obtenir les caractéristiques
        # du prochain créneau
        med_time, compartiment, id, orig_time = motor.get_next_schedule_compart(current_time)

        # création d'un autre log pour savoir si les créneaux ont été trouvés
        with open("/home/pi/Desktop/startup.txt","a") as f:
                f.write("run log: [" + str(datetime.now()) + "] no schedules found\n")

        # si aucun créneaux n'a été trouvé, dormir pendant 30s e refaire le processus
        if med_time == None:
            time.sleep(30)
            continue    
        # SHUTDOWN SYSTEM:
        # Si le compartiment du médicament est le numéro 9, la RaspBerry Pi va éteindre.
        # Il s'agit d'un mécanisme de déclenchement du Shutdown System de la RaspBerry Pi
        # Comme 
        compartiment = compartiment[0]
        if compartiment == 9:
            shutdown_time(5)
            with open("/home/pi/Desktop/startup.txt","a") as f:
                f.write("SHUTDOWN log: [" + str(datetime.now()) + "] started\n")
            break   
        # prendre la différence entre l'heure actuelle et le prochain créneau
        diff = motor.time_difference(med_time, current_time)
        
        if diff < 5 :
            print("FOUND")
            # le système 'dort' pendant le temps qui reste avant le créneau
            sleep(diff*60)
            print("it's time!")
            # on tourne le moteur à l'origine et vérifie si le bouton a été appuyé
            result = motor.rot_origin()
            print("move finished")

            # si le bouton a été appuyé, on va dispenser les médicaments
            if result:
                motor.spin_motor_alarm(compartiment+1)
                # supprimer le créneau de la base de données
                motor.s.delete(str(id))
                sleep(30)

            # le cas contraire, le mouvement est fini et on revient en stand by
            else:
                print("button not pressed")
                compartiment = str(compartiment)+",1"
                id = str(id)
                # on ajoute ',1' au numéro du compartiment pour qu'il soit affiché en 
                # rouge dnas l'application mobile
                motor.s.put(id, compartiment, orig_time, "name")
                sleep(60)
        # si la différence entre l'heure et le prochain créneau est supérieure à 5 min
        # le système 'dort' pour 30 seconde et refait le processus         
        else:
            print("not yet")
            sleep(30) # in the end will be 5 minutes

except Exception as e:

    print(e)
    with open("/home/pi/Desktop/startup.txt","a") as f:
        f.write("ERROR log: [" + str(datetime.now()) + "] " + str(e) +"\n")

