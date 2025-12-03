import fuzzy
import statistics
import csv
import os

enemy_types = ['Zombie','Skeleton','Enderman','Boss']
player_hp_values = [0, 2, 5, 8, 12, 16, 20]
enemy_hp_values  = [0, 3, 6, 10, 15, 20, 30]
mana_values      = [0, 10, 30, 60, 80, 100]
cd_val = 5

OUT_DIR = "experiments_out"
os.makedirs(OUT_DIR, exist_ok=True)

def summarize_list(vals):
    return (statistics.mean(vals), statistics.median(vals), statistics.pstdev(vals) if len(vals)>1 else 0.0)

# Scenario 1: compare 3 inference methods per entity over sample grid
def scenario_1():
    print("=== Scenario 1: compare inference methods per entity ===")
    methods = ['mamdani','sugeno','tsukamoto']
    results = { (etype, m): [] for etype in enemy_types for m in methods }

    for etype in enemy_types:
        for ph in player_hp_values:
            for eh in enemy_hp_values:
                for m in mana_values:
                    scores = fuzzy.get_all_scores(etype, ph, eh, 0, m, cd_val)
                    for meth, val in scores.items():
                        results[(etype,meth)].append(float(val))

    # aggregate and print
    best_by_entity = {}
    csv_rows = []
    for etype in enemy_types:
        stats = []
        for meth in methods:
            vals = results[(etype,meth)]
            avg, med, sd = summarize_list(vals)
            stats.append((meth, avg, med, sd))
            csv_rows.append([etype, 'scenario1', meth, avg, med, sd])
        stats_sorted = sorted(stats, key=lambda x: x[1], reverse=True)
        print(f"== {etype} ==")
        for meth, avg, med, sd in stats_sorted:
            print(f"  {meth:10s} avg={avg:.3f} med={med:.3f} sd={sd:.3f}")
        best_by_entity[etype] = stats_sorted[0][0]
        print()
    # save CSV
    with open(os.path.join(OUT_DIR, "scenario1_summary.csv"), "w", newline='') as f:
        w = csv.writer(f)
        w.writerow(["entity","scenario","method","avg","median","pstd"])
        w.writerows(csv_rows)
    return best_by_entity

# Scenario 2: compare best inference (from scenario1) vs no-fuzzy fallback heuristic
def scenario_2(best_by_entity):
    print("=== Scenario 2: compare best inference vs no-fuzzy (fallback heuristic) ===")
    methods = ['best_inference','no_fuzzy']
    csv_rows = []
    for etype in enemy_types:
        best = best_by_entity.get(etype)
        vals_best = []
        vals_fallback = []
        for ph in player_hp_values:
            for eh in enemy_hp_values:
                for m in mana_values:
                    scores = fuzzy.get_all_scores(etype, ph, eh, 0, m, cd_val)
                    vals_best.append(float(scores.get(best, scores.get('mamdani'))))
                    # use fallback scorers provided in module as "no-fuzzy" baseline
                    if etype in ('Zombie','Skeleton'):
                        fb = fuzzy.fallback_score_no_mana(ph, eh, cd_val)
                    else:
                        fb = fuzzy.fallback_score_with_mana(ph, eh, 0, m, cd_val)
                    vals_fallback.append(float(fb))
        b_avg, b_med, b_sd = summarize_list(vals_best)
        f_avg, f_med, f_sd = summarize_list(vals_fallback)
        csv_rows.append([etype, 'scenario2', best, b_avg, b_med, b_sd, 'fallback', f_avg, f_med, f_sd])
        print(f"{etype}: best={best}  best_avg={b_avg:.3f}  fallback_avg={f_avg:.3f}  delta={b_avg-f_avg:.3f}")
    with open(os.path.join(OUT_DIR,"scenario2_summary.csv"), "w", newline='') as f:
        w = csv.writer(f)
        w.writerow(["entity","scenario","best_method","best_avg","best_med","best_pstd","baseline_label","baseline_avg","baseline_med","baseline_pstd"])
        w.writerows(csv_rows)

# Scenario 3: test different membership interval configs (pass intervals to get_all_scores)
def scenario_3():
    print("=== Scenario 3: effect of different membership intervals ===")
    # define three example interval variants (keys follow fuzzy.get_membership_with_mana/get_membership_no_mana)
    interval_sets = {
        'default': None,
        'aggro_player_hp': {
            # make player-hp considered "low" earlier (aggressive AI towards low player hp)
            'hp_p_low':[0,0,10,30], 'hp_p_med':[20,35,55,75], 'hp_p_high':[50,80,100,100],
            # keep others default-ish
        },
        'defensive_enemy_hp': {
            # consider enemy hp "high" only near full so AI more defensive earlier
            'hp_b_low':[0,0,10,40], 'hp_b_med':[30,45,65,85], 'hp_b_high':[70,90,100,100],
        }
    }
    csv_rows = []
    for name, intervals in interval_sets.items():
        print(f"-- intervals: {name} --")
        for etype in enemy_types:
            methods = ['mamdani','sugeno','tsukamoto']
            vals_by_method = {m: [] for m in methods}
            for ph in player_hp_values:
                for eh in enemy_hp_values:
                    for m in mana_values:
                        scores = fuzzy.get_all_scores(etype, ph, eh, 0, m, cd_val, intervals=intervals)
                        for meth, val in scores.items():
                            vals_by_method[meth].append(float(val))
            for meth in methods:
                avg, med, sd = summarize_list(vals_by_method[meth])
                csv_rows.append([name, etype, meth, avg, med, sd])
                print(f" {etype:8s} {meth:10s} avg={avg:.3f} med={med:.3f} sd={sd:.3f}")
        print()
    with open(os.path.join(OUT_DIR,"scenario3_intervals.csv"), "w", newline='') as f:
        w = csv.writer(f)
        w.writerow(["interval_set","entity","method","avg","median","pstd"])
        w.writerows(csv_rows)

def main():
    best = scenario_1()
    scenario_2(best)
    scenario_3()
    print("All scenarios finished. Results written to", OUT_DIR)

if __name__ == '__main__':
    main()