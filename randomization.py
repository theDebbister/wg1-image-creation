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

    # print("Number of permutations for different scenarios:")
    # print(f'1. All permutations: {len(permutations)}')

    new_permutations = []

    equal_page_split = set()
    two_long_separate = set()
    not_two_consecutive_ins = set()
    not_two_consecutive_arg = set()
    two_long_not_consecutive = set()

    for version in permutations:
        ids_before_break = version[:5]
        ids_after_break = version[5:]

        pages = [STIMULUS_ECNODING[i]['pages'] for i in version]

        _, is_break_allowed = is_break_time_allowed(pages)
        if is_break_allowed:
            equal_page_split.add(version)

        # check if the two longest stimuli are separated in before and after break
        if is_before_and_after_break(version, 6, 7):
            two_long_separate.add(version)

        # two ins (ids 4 and 5) or two arg (ids 12 and 13) should not be consecutive
        if is_id_not_consecutive(version, 4, 5):
            not_two_consecutive_ins.add(version)

        if is_id_not_consecutive(version, 12, 13):
            not_two_consecutive_arg.add(version)

        # two longest stimuli should not be consecutive
        if is_id_not_consecutive(version, 6, 7):
            two_long_not_consecutive.add(version)

    all_combined_two_long_separate = equal_page_split.intersection(two_long_separate, not_two_consecutive_ins, not_two_consecutive_arg)
    all_combined_two_long_not_consecutive = equal_page_split.intersection(two_long_not_consecutive, not_two_consecutive_ins, not_two_consecutive_arg)
    minimal_criteria = equal_page_split.intersection(two_long_not_consecutive)

    print(f'1. All permutations: {len(permutations)}')
    print(f'2. Equal page split: {len(equal_page_split)}')
    print(f'3. Two longest stimuli separated: {len(two_long_separate)}')
    print(f'4. Two ins not consecutive: {len(not_two_consecutive_ins)}')
    print(f'5. Two arg not consecutive: {len(not_two_consecutive_arg)}')
    print(f'6. Two longest stimuli not consecutive: {len(two_long_not_consecutive)}')
    print(f'7. All combined two longest stimuli separated: {len(all_combined_two_long_separate)}')
    print(f'8. All combined two longest stimuli not consecutive: {len(all_combined_two_long_not_consecutive)}')
    print(f'9. Minimal criteria: {len(minimal_criteria)}')

    new_permutations = list(minimal_criteria)
    temp_perms = new_permutations.copy()
    final_permutations = []
    counts = [[0 for _ in range(10)] for _ in range(10)]
    max_count = 0
    seed = 0
    found = 10

    while len(final_permutations) < 100:
        if found < 10:
            random.seed(seed)
            random.shuffle(temp_perms)
            print(f'shuffled with seed {seed}')
            seed += 1
        else:
            temp_perms = sorted(temp_perms)

        found = 0

        for perm_index, perms in enumerate(temp_perms):
            # if all values in all list of count are equal to max count, then max_count += 1
            if found == 10:
                print(f'found 10 permutations')
                break

            if all(max_count == c for count in counts for c in count):
                max_count += 1

            for position, stimulus_id in enumerate(perms):
                updated_count = counts[stimulus_id - 4][position] + 1
                if updated_count > max_count:
                    break

            else:
                found += 1
                final_permutations.append(perms)
                temp_perms.pop(perm_index)
                for i, stimulus_id in enumerate(perms):
                    counts[stimulus_id - 4][i] += 1


def is_break_time_allowed(pages: list) -> (int, bool):
    # checks that break is after 5 stimuli AND as close to the middle as possible
    pages_until_break = 0
    difference = sum(pages)
    break_time = sum(pages) // 2

    for num_stimuli, i in enumerate(pages):
        pages_until_break += i

        if abs(pages_until_break - break_time) < difference:
            difference = abs(pages_until_break - break_time)

        # if the stimulus is farther away from the middle than the previous one, then break is not allowed
        else:
            if num_stimuli == 5 or num_stimuli == 6 or num_stimuli == 4:
                return num_stimuli, True

            return num_stimuli, False


def is_before_and_after_break(version: list, id_1: int, id_2: int) -> bool:
    # checks if two stimuli are before and after the break which is after 5 stimuli

    break_after, _ = is_break_time_allowed(version)

    ids_before_break = version[:break_after]
    ids_after_break = version[break_after:]

    if (id_1 in ids_before_break and id_2 in ids_after_break) or (id_1 in ids_after_break and id_2 in ids_before_break):
        return True

    return False


def is_id_not_consecutive(version: list, id_1: int, id_2: int) -> bool:
    # checks if two stimuli are not consecutive before and after the break
    # they are not consecutive if the break is in between them
    break_after, _ = is_break_time_allowed(version)

    ids_before_break = version[:break_after]
    ids_after_break = version[break_after:]

    if is_before_and_after_break(version, id_1, id_2):
        return True

    else:
        if id_1 in ids_before_break and id_2 in ids_before_break:
            # if the difference between their indices is 1, then they are consecutive
            if abs(ids_before_break.index(id_1) - ids_before_break.index(id_2)) == 1:
                return False
        else:
            if abs(ids_after_break.index(id_1) - ids_after_break.index(id_2)) == 1:
                return False

    return True


if __name__ == '__main__':
    create_permutations()
