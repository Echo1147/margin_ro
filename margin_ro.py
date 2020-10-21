from os import system
import pandas as pd
import numpy as np
import subprocess,shlex

path = 'si.inp' 
model = '.model'
inpout = 'A.TXT' #inp file output
output = 'result.csv' #margin output
command = 'jsim ' + path
devnull = open('dev/null', 'w') #spits jsim results to dev / null


def tocsv(fname: str):
    cname = fname.replace('TXT', 'csv')
    with open(fname, 'r') as file:
        filedata = file.read()
    filedata = filedata.replace(' ', ',')
    with open(cname, 'w') as file:
        file.write(filedata)

def judger(tri: int):
    p = subprocess.Popen(shlex.split(command), stdout=devnull, stderr=devnull)
    p_status = p.wait()
    tocsv(inpout)
    df = pd.read_csv('A.csv', header=None)
    st = np.empty((0), dtype=int)
    for i in range(tri):
        dtheta = df.iloc[int((i * period) + offset + (0.3 * period)), 1] - df.iloc[int((i * period) + offset - (0.3 * period)), 1]
        #noddev = df.iloc[i*10000+4500:i*10000+5500, 1]
        #noddev_mean = noddev.mean() * 10 ** 6
        if dtheta > 20:
            st = np.append(st, 1)
        elif dtheta < 20:
            st = np.append(st, 0)
        else:
            print('error: judger')
    a = int(0)
    for i in range(tri):
        if st[i] == operation[i]:
            a += 1
    if a == tri:
        return 1
    else:
        return 0
    
def replace_inp(obj: str, val: str, tri: int):
    #open the inp file
    with open(path) as f:
        lines = f.readlines()
    
    #extract the intended circuit parameter
    lines_strip = [line.strip() for line in lines]
    lines_ext = [line for line in lines_strip if obj in line]
    l_obj = lines_ext[0]
    l_list = l_obj.split()
    
    #change the circuit parameter
    if ('I' in obj) == True:
        for i in range(tri):
            l_list[8 * (i+1)] = val + 'uA'
            l_list[8 * (i+1) + 2] = val + 'uA'
        l_ins = ' '.join(l_list) + '\n'
    elif (('k' in obj) == True) and (('I' in obj) == False):
        l_list[3] = val
        l_ins = ' '.join(l_list) + '\n'
    elif (('L' in obj) == True) and (('I' in obj) == False):
        l_list[3] = val + 'ph'
        l_ins = ' '.join(l_list) + '\n'
    else:
        print("error: invalid circuit element name")
    
    #Write changes to inp file
    with open(path, 'r') as f1:
        tmp_list =[]
        for row in f1:
            if row.find(obj) != -1:
                tmp_list.append(l_ins)
            else:
                tmp_list.append(row)                   
    with open(path, 'w') as f2:
        for i in range(len(tmp_list)):
            f2.write(tmp_list[i])

def loop(obj: str, design: int, trial: int):
    margin = np.array((0, 0), dtype=int)
    value = np.array((0, 0), dtype=float)
    replace_inp(obj, str(design), trial)
    result_i = judger(trial)
    for i in range(2):
        d = design + (design * ((-1) ** (i+1)))
        replace_inp(obj, str(d), trial)
        result_c = judger(trial)
        if result_c == 1:
            margin[i] = 100 * ((-1) ** (i+1))
            value[i] = d
        elif result_c == 0:
            d = d - (design/2) * ((-1) ** (i+1))
            for j in range(7):
                replace_inp(obj, str(d), trial)
                result_j = judger(trial)
                d = d + (design/(2**(j+2))) * ((-1) ** (i+1)) * ((-1) ** (result_j+1))
            margin[i] = round(((d-design)/design)*100)
            value[i] = d
        else:
            print('error: loop judge')
            
    if result_i == 0:
        if margin[0] == 0:
            sgn = 0
        elif margin[1] == 0:
            sgn = 1
        else:
            print('error: result_i')

        d = d + ((design/2) * ((-1) ** (sgn+1)))
        for k in range(7):
            replace_inp(obj, str(d), trial)
            result_j = judger(trial)
            d = d + (design/(2**(k+2))) * ((-1) ** (result_j+1)) * ((-1) ** (sgn+1))
        margin[sgn] = round(((d-design)/design)*100)
        value[sgn] = d
    
    replace_inp(obj, str(design), trial)
    return margin, value

def init(model):
    for i in range(len(element)):
        replace_inp(element[i], str(design[i]), trial)
    with open(path) as f:
        lines = f.readlines()
    #extract the intended circuit parameter
    lines_strip = [line.strip() for line in lines]
    lines_ext = [line for line in lines_strip if model in line]
    l_obj = lines_ext[0]
    l_list = l_obj.split()
    return l_list[7].rstrip(')')           

element = ['Isq_bias1', 'Isq_flux1', 'Iqfp1', 'ksq1_qfp1']
design = [44, 20, 350, 0.359]
operation = [0, 1, 0, 1]
trial = len(operation)
offset = int(5000)
period = int(10000)

Icrit = init(model)
title = '\nmargin: ' + Icrit + '\n'
print(title)

for i in range(trial):
    a ,b = loop(element[i], design[i], trial)
    s = element[i] + ',' + str(a[0]) +  ',' + str(a[1]) +  ',' + str(design[i]) +  ',' + str(b[0]) +  ',' + str(b[1]) +  ',' + str((b[0]+b[1])/2) + '\n'
    print('{0:12}: {1:>4} % ~{2:>4} % | median = {3:<}'.format(element[i], str(a[0]), str(a[1]), str((b[0]+b[1])/2)))
    with open(output, mode='a') as f:
        if i == 0:
            f.write(title + 'element,low (%),high (%),design,min,max,median\n')
        f.write(s)


#replace_inp("Isq_bias1", str(40), 4) 
