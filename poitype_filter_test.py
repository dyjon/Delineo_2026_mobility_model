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

    output = open("experiment_output.txt",'w')
    
    #what group each location type is
    type_groups = []

    #the range of group numbers
    num_groups = int(input("Type the number of groups to form."))
    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)

    #start by putting everyone in random groups
    for i in all_types:
        type_groups.append(random.choice(group_nums))


    #place every type in the same group as the type most similar to it (using Levenshtein curve)
    max_sim = 0.0
    for j in range(len(all_types)):
        for k in range(len(all_types)):
            cur_sim = Levenshtein.ratio(all_types[j], all_types[k])
            if j != k and cur_sim > max_sim:
                max_sim = cur_sim
                type_groups[j] = type_groups[k]

        max_sim = 0.0

    #write results to txt

    for a in range(len(group_nums)):
        output.write(f"GROUP {a}:\n")
        for b in range(len(all_types)):
            if type_groups[b] == group_nums[a]:
                output.write(f"{all_types[b]}\n")

    #find the group with the highest total similarity to the target, then output that group
    best_group = -1
    group_ranking = [0]*num_groups
    for a in range(len(group_nums)):
        for b in all_types:
            if type_groups[b] == group_nums[a]:
                group_ranking[(group_nums[a])] += Levenshtein.ratio(target, all_types[b])

    for b in range(len(group_ranking)):
        if b == 0:
            best_group = b
        else:
            if group_ranking[b] > group_ranking[b-1]:
                best_group = b

    output.close()

    return best_group

#separation of sim model into multiple usable functions, given we have all POIs formatted as POI objects
def get_all_types(pois):
    all_types = []
    for p in pois:
        if p.loc_type not in all_types:
            all_types.append(p.loc_type)

    return all_types

def get_type_groups(all_types):
    #what group each location type is
    type_groups = []
        
    #the range of group numbers
    # num_groups = int(input("Type the number of groups to form.")) SET GROUPS TO 40 FOR NOW
    num_groups = 40
    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)
        
    #start by putting everyone in random groups
    for i in all_types:
        type_groups.append(random.choice(group_nums))
        
        
    #place every type in the same group as the type most similar to it (using Levenshtein curve)
    max_sim = 0.0
    for j in range(len(all_types)):
        for k in range(len(all_types)):
            cur_sim = Levenshtein.ratio(all_types[j], all_types[k])
            if j != k and cur_sim > max_sim:
                max_sim = cur_sim
                type_groups[j] = type_groups[k]
        
        max_sim = 0.0

    return type_groups


def get_best_group(target, all_types, type_groups):
    #the range of group numbers
    # num_groups = int(input("Type the number of groups to form.")) SET GROUPS TO 40 FOR NOW
    num_groups = 40
    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)

    #find the group with the highest total similarity to the target, then output that group
    best_group = -1
    group_ranking = [0]*num_groups
    for a in range(len(group_nums)):
        for b in all_types:
            if type_groups[b] == group_nums[a]:
                group_ranking[(group_nums[a])] += Levenshtein.ratio(target, all_types[b])
    
    for b in range(len(group_ranking)):
        if b == 0:
            best_group = b
        else:
            if group_ranking[b] > group_ranking[b-1]:
                best_group = b

        return best_group

if __name__ == "__main__":
    main()