import itertools
from collections import Counter, defaultdict
import random

from tqdm import tqdm

STIMULUS_ECNODING = {
    4: {
        'name': 'Ins_HumanRights',
        'pages': 9,
        'type': 'ins'
    },
    5: {
        'name': 'Ins_EURLex',
        'pages': 9,
        'type': 'ins'
    },
    6: {
        'name': 'Lit_Alchemist',
        'pages': 6,
        'type': 'lit'
    },
    7: {
        'name': 'Lit_EmperorClothes',
        'pages': 18,
        'type': 'lit'
    },
    8: {
        'name': 'Lit_MagicMountain',
        'pages': 6,
        'type': 'lit'
    },
    9: {
        'name': 'Lit_NorthWind',
        'pages': 2,
        'type': 'lit'
    },
    10: {
        'name': 'Lit_Solaris',
        'pages': 19,
        'type': 'lit'
    },
    11: {
        'name': 'Lit_BrokenApril',
        'pages': 11,
        'type': 'lit'
    },
    12: {
        'name': 'Arg_PISARapaNui',
        'pages': 15,
        'type': 'arg'
    },
    13: {
        'name': 'Arg_PISACowsMilk',
        'pages': 14,
        'type': 'arg'
    },

}

TOTAL_PAGES = sum([STIMULUS_ECNODING[id]['pages'] for id in STIMULUS_ECNODING])


def create_permutations() -> None:

    # create all possible permutations of the 11 stimuli by stimulus id that ranges from 3-13

    block_1 = [4, 7, 8, 9, 12]
    block_2 = [5, 6, 10, 11, 13]

    all_perm_block_1 = len(list(itertools.permutations(block_1)))
    all_perm_block_2 = len(list(itertools.permutations(block_2)))



    stimuli_ids = [i for i in range(4, 14)]

    permutations = list(itertools.permutations(stimuli_ids))

    #print("Number of permutations for different scenarios:")
    #print(f'1. All permutations: {len(permutations)}')

    equal_page_split = 0
    two_long_separate = 0
    equal_page_split_two_long_separate = 0
    equal_page_split_two_long_separate_not_two_ins_not_two_arg = 0
    equal_page_split_two_long_separate_ins_and_arg_separate = 0

    new_permutations = []

    for version in permutations:
        ids_before_break = version[:5]
        ids_after_break = version[5:]
        pages = [STIMULUS_ECNODING[i]['pages'] for i in version]

        pages_until_break = 0
        difference = TOTAL_PAGES
        break_time = TOTAL_PAGES // 2
        for num_stimuli, i in enumerate(pages):
            pages_until_break += i

            if abs(pages_until_break - break_time) < difference:
                difference = abs(pages_until_break - break_time)
                break_time = pages_until_break

            else:
                if num_stimuli - 1 == 4:
                    equal_page_split += 1
                    if (6 in ids_before_break and 7 in ids_after_break) or (6 in ids_after_break and 7 in ids_before_break):
                        equal_page_split_two_long_separate += 1

                        for i in range(1, 5):
                            stimulus_id_1 = ids_before_break[i]
                            stimulus_id_before_1 = ids_before_break[i-1]
                            stimulus_id_2 = ids_after_break[i]
                            stimulus_id_before_2 = ids_after_break[i-1]
                            if STIMULUS_ECNODING[stimulus_id_1]['type'] == 'arg' and STIMULUS_ECNODING[stimulus_id_before_1]['type'] == 'arg':
                                break
                            elif STIMULUS_ECNODING[stimulus_id_1]['type'] == 'ins' and STIMULUS_ECNODING[stimulus_id_before_1]['type'] == 'ins':
                                break
                            elif STIMULUS_ECNODING[stimulus_id_2]['type'] == 'arg' and STIMULUS_ECNODING[stimulus_id_before_2]['type'] == 'arg':
                                break
                            elif STIMULUS_ECNODING[stimulus_id_2]['type'] == 'ins' and STIMULUS_ECNODING[stimulus_id_before_2]['type'] == 'ins':
                                break
                        else:
                            equal_page_split_two_long_separate_not_two_ins_not_two_arg += 1
                            new_permutations.append(version)

        # check if the two long stimuli are separated in before an after break
        if 6 in ids_before_break and 7 in ids_after_break:
            two_long_separate += 1
        elif 6 in ids_after_break and 7 in ids_before_break:
            two_long_separate += 1

    prev_largest = 0

    # best seed so far: 366 with 37 permutations
    for seed in tqdm(range(500, 1000)):
        temp_perms = new_permutations.copy()
        random.seed(seed)
        random.shuffle(temp_perms)
        final_permutations = []
        counts = [[0 for i in range(10)] for j in range(10)]
        max_count = 0
        found = True
        while found:
            for perm_index, perms in enumerate(temp_perms):
                found = False
                # if all values in all list of count are equal to max count, then max_count += 1
                if all(max_count == c for count in counts for c in count):
                    max_count += 1

                # add position of each stimuli to the last positions
                for position, stimulus_id in enumerate(perms):
                    # make sure all stimuli have a different position
                    updated_count = counts[stimulus_id - 4][position] + 1
                    if updated_count > max_count:
                        break
                else:
                    found = True
                    final_permutations.append(perms)
                    temp_perms.pop(perm_index)
                    for i, stimulus_id in enumerate(perms):
                        counts[stimulus_id - 4][i] += 1

        if len(final_permutations) > prev_largest:
            print(seed)
            print(max_count)
            print(len(final_permutations))
            prev_largest = len(final_permutations)


    # print(f'2. Two longest before and after break: {two_long_separate}')
    # print(f'3. Break after 5: {equal_page_split}')
    # print(f'4. Break after 5 + two longest before and after break: {equal_page_split_two_long_separate}')
    # print(f'5. Break after 5 + two longest before and after break + no consecutive ins + no consecutive arg: {equal_page_split_two_long_separate_not_two_ins_not_two_arg}')
    # print(f'6. Previous block structure: {all_perm_block_2 * all_perm_block_1}')


if __name__ == '__main__':
    create_permutations()

