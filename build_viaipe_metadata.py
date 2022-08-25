POPS_FILE = "pop_lat_lon.txt"
pops = {}

def load_pops(filename=POPS_FILE):
    with open(filename, "r") as f:
        for line in f:
            items = line.strip().split(";")
            pops[items[3]] = items[0] # pops[pop_id] = pop_name


def z5(s): return ("00000"+s)[-5:]


def recover_caption(s):
    begin = None
    caption_count = 0
    ignore = ["-", "|", "/"]
    special = ["Á", "É", "Í", "Ó", "Ú", "Ç"]
    states = [
        "AC", "AL", "AM", "AP", "BA", "CE",
        "DF", "ES", "GO", "MA", "MG", "MS",
        "MT", "PA", "PB", "PE", "PI", "PR",
        "RJ", "RN", "RO", "RR", "RS", "SC",
        "SE", "SP", "TO"
    ]

    for i in range (len(s)):
        c = s[i]
        # if c in ignore:
        #     if begin is not None:
        #         caption_count += 1
        #     continue

        if "A" <= c <= "Z" or c in special:
            caption_count += 1

            if caption_count == 2:
                if begin is None:
                    begin = i-1

        elif begin is None:
            caption_count = 0
        else:
            break
    
    if begin is None:
        return s

    caption = s[begin:begin+caption_count]

    if caption in states:
        return s

    if caption[-1] in ignore:
        caption = caption[:-1]
    
    return caption


if __name__ == "__main__":
    load_pops()
    
    with open("clients.txt", "r") as f, open("viaipe_metadata.json", "w") as fout:
        recs = []
        for line in f:
            rec = line.strip().split(";")
            recs.append(rec)
        
        x = sorted(recs, key=lambda item: '$'+z5(item[0])+'$'+z5(item[2])+'$'+z5(item[6])) # item = []
        
        print('{ "pops": {', file=fout)
        pop_name = None
        last_pop = ""
        last_client = ""
        last_interface = ""
        for rec in x:
            print(rec)
            '''
            ['27', 'EMBRAPA-CNPASA', '28', '-10.1403', '-48.3141', 'e12636', '5']
            ['27', 'UNITINS', '29', '-10.191', '-48.3166', 'e12767', '1']
            ['27', 'UNITINS', '29', '-10.191', '-48.3166', 'e12247', '2']
            ['27', 'UNITINS', '29', '-10.191', '-48.3166', 'e12377', '3']
            ['27', 'UNITINS', '29', '-10.191', '-48.3166', 'e12507', '4']
            ['27', 'UNITINS', '29', '-10.191', '-48.3166', 'e12637', '5']
            '''
            
            if last_pop != rec[0]:
                last_client = ""
                last_interface = ""
                if last_pop != "":
                    print("]}]},", file=fout) # fecha cliente, clientes e pop


                last_pop = rec[0]
                pop_name = pops[last_pop]
                print('"'+pop_name+'": { "clientes": [', file=fout) # abre pop e clientes


            if last_client != rec[2]:
                last_interface = ""
                if last_client != "":
                    print("]},", file=fout) # fecha interfaces e cliente
                
                last_client = rec[2]


                client = '{"name": "'+rec[1]+'", "id": '+rec[2]+', "lat": '+rec[3]+', "lon": '+rec[4]+',"interfaces": ['
                print(client, file=fout)


            if last_interface == "":
                print('{ "name": "'+rec[5]+'", "id": '+ rec[6] +' }', file=fout)
                last_interface = rec[5]
            else:
                # adiciona interfaces
                print(',{ "name": "'+rec[5]+'", "id": '+ rec[6] +' }', file=fout)
        
        print("]}]}}}", file=fout) # fecha interface, cliente, clientes, pop, pops e objeto
