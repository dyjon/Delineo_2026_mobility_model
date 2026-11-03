import csv
import sys
import Levenshtein
import random

def main():

    target = str(input("Type the keyword to check for. "))
    target = target.lower()

    if len(sys.argv) > 1:
        sim_model(target)
        
    else:
        print("Insufficient command line arguments\n")

    return 1

def basic_model(target: str):

    matches_gen = []
    matches_spec = []
    for i in range(1,len(sys.argv)):
        with open(sys.argv[i], 'r', encoding='utf-8', errors='ignore') as f:
            data = csv.reader(f)
            for row in data: 
                #Dewey: categories are 28 (specific) and 30 (general). Jingcheng data: categories are 5 (general) and 6 (specific).
                if (str(row[4]).lower()).find(target) != -1 and (str(row[4]).lower()) not in matches_gen:
                    matches_gen.append(str(row[4]).lower())
                if (str(row[5]).lower()).find(target) != -1 and (str(row[5]).lower()) not in matches_spec:
                    matches_spec.append(str(row[5]).lower())
    
                if len(row) >= 30 and (str(row[29]).lower()).find(target) != -1 and (str(row[29]).lower()) not in matches_gen:
                    matches_gen.append(str(row[29]).lower())
                if len(row) >= 28 and (str(row[27]).lower()).find(target) != -1 and (str(row[27]).lower()) not in matches_spec:
                    matches_spec.append(str(row[27]).lower())
    
    print("GENERAL:\n")
    for a in matches_gen:
        print(f"{a}\n")
    
    print("SPECIFIC:\n")
    for b in matches_spec:
        print(f"{b}\n")

    return 1

def sim_model(target: str):

    all_types = []
    #grab a list of all location types 
    for i in range(1,len(sys.argv)):
            with open(sys.argv[i], 'r', encoding='utf-8', errors='ignore') as f:
                data = csv.reader(f)
                for row in data: 
                    #Dewey: categories are 28 (specific) and 30 (general). Jingcheng data: categories are 5 (general) and 6 (specific).
                    if (str(row[4]).lower()) not in all_types:
                        all_types.append(str(row[4]).lower())
                    if (str(row[5]).lower()) not in all_types:
                        all_types.append(str(row[5]).lower())
        
                    if len(row) >= 30 and (str(row[29]).lower()) not in all_types:
                        all_types.append(str(row[29]).lower())
                    if len(row) >= 28 and (str(row[27]).lower()) not in all_types:
                        all_types.append(str(row[27]).lower())

    #what group each location type is
    type_groups = []
    #the range of group numbers
    group_nums = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

    #start by putting everyone in random groups
    for i in all_types:
        type_groups.append(random.choice(group_nums))

    #place every type in the same group as the type most similar to it (using Levenshtein curve)
    max_sim = 0.0
    for j in range(len(all_types)):

        for k in range(len(all_types)):
            cur_sim = Levenshtein.ratio(all_types[j], all_types[k])
            if cur_sim > max_sim:
                max_sim = cur_sim
                type_groups[j] = type_groups[k]

        max_sim = 0.0

    #print results
    for a in range(len(group_nums)):
        print(f"GROUP {a}:\n")
        for b in range(len(all_types)):
            if type_groups[b] == group_nums[a]:
                print(f"{all_types[b]}\n")

    return 1

if __name__ == "__main__":
    main()