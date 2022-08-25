import sys
import os
import gzip
import json
import time

TARGET_FILE = "1d.json.gz"
DST_FOLDER = "tc"
LAST_LINE_SZ = 30 # "# /YYYY/MM/DD/HH/mm/1d.json.gz"
FUSO_BRASIL = 10800 # precisa tirar a diferenca do gmtime

# INTERFACE_DATA = ["discard_out", "tipo", "max_traffic_up", "nome", "traffic_graph_id",
                 # "avg_in", "avg_out", "max_traffic_down", "error_in", "error_out",
                 # "errors_graph_id", "client_side", "traffic_in", "discard_in", "max_in"]

#SMOKE_DATA = ["loss", "avg_val", "max_loss", "val", "max_val", "avg_loss"]


INTERFACE_DATA = [ "nome", "avg_in", "avg_out", "max_in", "max_out"]

SMOKE_DATA = ["val", "avg_val", "max_val", "loss", "avg_loss", "max_loss"]

POPS_FILE = "pop_lat_lon.txt"
pops = {}

CLIENTS_FILE = "clients.txt"
NEW_CLIENTS_FILE = "new_"+CLIENTS_FILE
clients = {}


def create_folders(path):
    full_path = ""
    for folder in path.split("/"):
        full_path += folder + "/"
        create_folder(full_path)

def create_folder(folder):
    try:
        os.mkdir(folder)
    except OSError: pass



def load_pops(filename=POPS_FILE):
    with open(filename, "r") as f:
        for line in f:
            items = line.strip().split(";")
            pops[items[0]] = items[3] # pops[pop_name] = pop_id


##################################
# Functions to manage clients dict
##################################

def load_clients(filename=CLIENTS_FILE):
    try:
        with open(filename,"r") as fr:
            for line in fr:
                pop_id,client_name,client_id,client_lat,client_lon,interface_name,interface_id = line.strip().split(";")

                if pop_id not in clients: clients[pop_id] = {}
                if client_name not in clients[pop_id]: clients[pop_id][client_name] = {}

                clients[pop_id][client_name]["id"] = client_id # client_id
                clients[pop_id][client_name]["lat"] = client_lat
                clients[pop_id][client_name]["lon"] = client_lon
                clients[pop_id][client_name][interface_name] = interface_id # interface_id
    except FileNotFoundError:
        f = open(filename, "x") # cria o arquivo se ele não existe
        f.close()


def check_client_id(pop_id, client_name, client_lat, client_lon):
    if pop_id not in clients:
        clients[pop_id] = {}
    
    if client_name not in clients[pop_id]:
        clients[pop_id][client_name] = {"id": len(clients[pop_id]) + 1}
        clients[pop_id][client_name]["lat"] = client_lat
        clients[pop_id][client_name]["lon"] = client_lon
    
    return clients[pop_id][client_name]["id"]

def check_interface_id(pop_id, client_name, interface_name, filename2=NEW_CLIENTS_FILE):
    client = clients[pop_id][client_name]
    if interface_name not in client:
        client[interface_name] = len(clients[pop_id][client_name]) -2 # len() -3 +1 = -2
        with open(filename2, "a") as f:
            line = "{};{};{};{};{};{};{}".format(pop_id, client_name, client["id"], client["lat"], client["lon"], interface_name, client[interface_name])
            print(line, file=f)
    
    return client[interface_name]


def att_clients_file(filename=CLIENTS_FILE, filename2=NEW_CLIENTS_FILE):
    try:
        with open(filename,"r") as f1, open(filename2,"r") as f2, open("temp.txt","w") as f3:
            for line in f1:
                f3.write(line)
            for line in f2:
                f3.write(line)
        os.remove(filename)
        os.remove(filename2)
        os.rename(r'{}'.format(os.path.join("temp.txt")), r'{}'.format(os.path.join(filename)))
    except FileNotFoundError:
        pass # no att to be made

######################################

####################################
# Functions to process viaipe data
####################################

def bps2int(bps):
    return int(bps/8)

def rate2int(rate):
    return int(rate * 100)

####################################



def process_and_save(raw_file):
    used_in = set() # which tc files were written using raw_file
    with gzip.open(raw_file, 'rt') as fin:
        data = ""
        for line in fin: data += line
        
        json_obj = json.loads(data)
        for region in json_obj["children"]:
            for pop in region["children"]:
                #print(pop["name"])
                pop_id = pops.get(pop["id"].lower())
                if pop_id is None:
                    print("Invalid PoP: {}".format(pop["id"]))
                    continue

                pop_epoch = int(pop["generation_date"].split("|")[0][:-2]) # generation_date = "1656281870.0|10800"

                #date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(pop_epoch - FUSO_BRASIL)) # convert epoch to str
                tm = time.gmtime(pop_epoch - FUSO_BRASIL)
                seconds = ("0"+str(tm.tm_sec))[-2:]
                minutes = ("0"+str(tm.tm_min))[-2:]
                hour = ("0"+str(tm.tm_hour))[-2:]
                day = ("0"+str(tm.tm_mday))[-2:]
                month = ("0"+str(tm.tm_mon))[-2:]
                year = str(tm.tm_year)
                
                tc_file_dir = "{}/{}/{}".format(DST_FOLDER, year, month)
                tc_file_name = "{}{}{}_{}_00.csv".format(year, month, day, hour)
                tc_file_path = "{}/{}".format(tc_file_dir, tc_file_name)
                
                timestamp = "{}-{}-{} {}:{}:{}".format(year, month, day, hour, minutes, seconds)

                create_folders(tc_file_dir)
                last_used_file = None
                try:
                    with open(tc_file_path, "rb") as bin_f:
                        bin_f.seek(-2, os.SEEK_END)
                        while bin_f.read(1) != b'\n':
                            bin_f.seek(-2, os.SEEK_CUR)
                        last_used_file = bin_f.readline().decode()
                        if last_used_file[0] == "#": last_used_file = last_used_file.strip().split(" ")[1]
                        else: last_used_file = None
                except FileNotFoundError or OSError:
                    pass
                if last_used_file:
                    raw_year, raw_month, raw_day, raw_hour, raw_min = list(map(int, raw_file.split("/")[-6:-1]))
                    last_year, last_month, last_day, last_hour, last_min = list(map(int, last_used_file.split("/")[-6:-1]))
                    if raw_year < last_year:
                        #print("Skipping",raw_file)
                        continue # older file
                    if raw_month < last_month:
                        #print("Skipping",raw_file)
                        continue # older file
                    if raw_day < last_day:
                        #print("Skipping",raw_file)
                        continue # older file
                    if raw_hour < last_hour:
                        #print("Skipping",raw_file)
                        continue # older file
                    if raw_min <= last_min:
                        #print("Skipping",raw_file)
                        continue # older/same file
                
                used_in.add(tc_file_path)
                fout = open(tc_file_path, "a")
                for client in pop["children"]:
                    client_id = check_client_id(pop_id, client["name"], client["lat"],client["lng"])
                    line_prefix = "{};{};{};{};{}".format(timestamp,client["lat"],client["lng"],pop_id,client_id)


                    # Getting interface(s) data
                    interfaces_lines = []
                    for interface in client["data"]["interfaces"]: # array of interfaces
                        interface_id = check_interface_id(pop_id, client["name"], interface[INTERFACE_DATA[0]])
                        interfaces_lines.append(";"+str(interface_id))
                        for key in INTERFACE_DATA[1:]:
                            val = interface.get(key)
                            if val is None:
                                interfaces_lines[-1] += ";0"
                                continue

                            val = bps2int(val)

                            interfaces_lines[-1] += ";"+str(val)


                    # Getting smoke data
                    smoke_line = "" # sufix
                    if "smoke" in client["data"]:
                        smoke = client["data"]["smoke"]
                        for key in SMOKE_DATA:
                            val = smoke.get(key)
                            if val is None:
                                smoke_line += ";0"
                                continue

                            val = rate2int(val)

                            smoke_line += ";"+str(val)
                    else:
                        smoke_line += ";0"*len(SMOKE_DATA)


                    for interface_line in interfaces_lines:
                        print(line_prefix+interface_line+smoke_line, file=fout)

                fout.close()

    # /home/borescope/viaipe/data/2022/6/26/1/1/1d.json.gz
    items = raw_file.split("/")
    last_line = "# /{}/{}/{}/{}/{}/{}".format(items[-6],items[-5],items[-4],items[-3],items[-2],items[-1])
    last_line += "_"*(LAST_LINE_SZ-len(last_line))
    for tc_file in used_in:
        with open(tc_file, "a") as f:
            print(last_line, file=f)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Missing argument <data-path>")
        print("Example: python3 data2tc.py /home/borescope/viaipe/data/2022/6/26/")
        sys.exit(1)
    
    path = sys.argv[1]
    
    load_pops()
    load_clients()
    fnames = []
    for item in os.walk(path): # item = (path, dirnames, filenames)
        if len(item[2]) == 0: continue
        f_fullname = item[0] + "/" + TARGET_FILE
        raw_year, raw_month, raw_day, raw_hour, raw_min = f_fullname.split("/")[-6:-1]
        
        fulldate = raw_year+("0" + raw_month)[-2:]+("0" + raw_day)[-2:]+("0" + raw_hour)[-2:]+("0" + raw_min)[-2:]
        fnames.append([f_fullname, fulldate])

    for fname in sorted(fnames, key=lambda item: item[1]): # fname = (fullpath, file_date)
        
        #f_fullname = item[0] + "/" + TARGET_FILE
        f_fullname, _ = fname
        print("Processing",f_fullname)
        try:
            process_and_save(f_fullname)
        except Exception as e:
            print("Process and Save Exception:",e)
    
    att_clients_file()
