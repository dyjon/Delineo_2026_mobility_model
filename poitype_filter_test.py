import csv
import sys
import Levenshtein
import random

def main():

    target = str(input("Type the keyword to check for. "))
    target = target.lower()

    if len(sys.argv) > 1:
        print(sim_model(target))
        
    else:
        print("Insufficient command line arguments\n")

    return 1

def basic_model(target: str):

    matches_gen = []
    matches_spec = []
    for i in range(1,len(sys.argv)):
        with open(sys.argv[i], 'r', encoding='utf-8', errors='ignore') as f:
            data = csv.reader(f)
            next(data, None)

            for row in data: 
                #Dewey: categories are 28 (specific) and 30 (general). Jingcheng data: categories are 5 (general) and 6 (specific).
                if len(row) < 6:
                    continue

                if len(row) >= 30:
                    gen, spec = row[29].lower(), row[27].lower()

                else:
                    gen, spec = row[4].lower(), row[5].lower()

                if target in gen and gen not in matches_gen:
                    matches_gen.append(gen)

                if target in spec and spec not in matches_spec:
                    matches_spec.append(spec)

    print("GENERAL:\n")
    for a in matches_gen:
        print(f"{a}\n")
    
    print("SPECIFIC:\n")
    for b in matches_spec:
        print(f"{b}\n")

    return 1

def sim_model(target: str):
    rng = random.Random(42)
    all_types = []
    # grab a list of all location types 
    for i in range(1,len(sys.argv)):
            with open(sys.argv[i], 'r', encoding='utf-8', errors='ignore') as f:
                data = csv.reader(f)
                next(data, None)

                for row in data: 
                    # Dewey: categories are 28 (specific) and 30 (general). Jingcheng data: categories are 5 (general) and 6 (specific).
                    if len(row) < 6:
                        continue

                    if len(row) >= 30:
                        gen, spec = row[29].lower(), row[27].lower()

                    else:
                        gen, spec = row[4].lower(), row[5].lower()

                    if gen and gen not in all_types:
                        all_types.append(gen)

                    if spec and spec not in all_types:
                        all_types.append(spec)

    if not all_types:
        raise ValueError("No valid location types found.")

    output = open("experiment_output.txt",'w')

    # what group each location type is
    type_groups = []

    # the range of group numbers
    num_groups = int(input("Type the number of groups to form."))
    if num_groups <= 0:
        raise ValueError("Number of groups must be positive.")

    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)

    # start by putting everyone in random groups
    for i in all_types:
        type_groups.append(rng.choice(group_nums))


    # place every type in the same group as the type most similar to it (using Levenshtein curve)
    max_sim = 0.0
    for j in range(len(all_types)):
        for k in range(len(all_types)):
            cur_sim = Levenshtein.ratio(all_types[j], all_types[k])
            if j != k and cur_sim > max_sim:
                max_sim = cur_sim
                type_groups[j] = type_groups[k]

        max_sim = 0.0

    # write results to txt

    for a in range(len(group_nums)):
        output.write(f"GROUP {a}:\n")
        for b in range(len(all_types)):
            if type_groups[b] == group_nums[a]:
                output.write(f"{all_types[b]}\n")

    # find the group with the highest average similarity to the target, then output that group
    best_group = get_best_group(target, all_types, type_groups)
    output.close()

    return best_group

# separation of sim model into multiple usable functions, given we have all POIs formatted as POI objects
def get_all_types(pois):
    all_types = []
    for p in pois:
        if p.loc_type not in all_types:
            all_types.append(p.loc_type)

    return all_types

def get_type_groups(all_types):
    # what group each location type is
    rng = random.Random(42)
    type_groups = []

    # the range of group numbers
    # num_groups = int(input("Type the number of groups to form."))
    num_groups = 40
    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)
        
    #start by putting everyone in random groups
    for i in all_types:
        type_groups.append(rng.choice(group_nums))
        
        
    # place every type in the same group as the type most similar to it (using Levenshtein curve)
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
    # the range of group numbers
    # num_groups = int(input("Type the number of groups to form."))
    num_groups = max(type_groups) + 1
    group_nums = []
    for i in range(num_groups):
        group_nums.append(i)

    # find the group with the highest average similarity to the target, then output that group
    best_group = -1
    max_average = float('-inf')
    group_ranking = [0] * num_groups

    for i in range(len(all_types)):
        group_ranking[type_groups[i]] += Levenshtein.ratio(target, all_types[i])

    for i in range(num_groups):
        count = type_groups.count(i)

        if count > 0:
            average = group_ranking[i] / count

            if average > max_average:
                max_average = average
                best_group = i

    return best_group

if __name__ == "__main__":
    main()
