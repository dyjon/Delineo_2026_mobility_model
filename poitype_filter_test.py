import csv
import sys
import unicodedata

def main():
    matches_gen = []
    matches_spec = []
    target = str(input("Type the keyword to check for. "))
    target = target.lower()

    if len(sys.argv) > 1:
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
    else:
        print("Insufficient command line arguments\n")

    return 1

if __name__ == "__main__":
    main()