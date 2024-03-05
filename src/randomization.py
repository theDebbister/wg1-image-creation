import itertools
from collections import Counter, defaultdict
import random

from tqdm import tqdm

STIMULUS_ENCODING = {
    2: {
        'name': 'Ins_HumanRights',
        'pages': 9,
        'type': 'ins'
    },
    3: {
        'name': 'Ins_LearningMobility',
        'pages': 9,
        'type': 'ins'
    },
    4: {
        'name': 'Lit_Alchemist',
        'pages': 6,
        'type': 'lit'
    },
    5: {
        'name': 'Lit_EmperorClothes',
        'pages': 18,
        'type': 'lit'
    },
    6: {
        'name': 'Lit_MagicMountain',
        'pages': 6,
        'type': 'lit'
    },
    7: {
        'name': 'Lit_NorthWind',
        'pages': 2,
        'type': 'lit'
    },
    8: {
        'name': 'Lit_Solaris',
        'pages': 19,
        'type': 'lit'
    },
    9: {
        'name': 'Lit_BrokenApril',
        'pages': 11,
        'type': 'lit'
    },
    11: {
        'name': 'Arg_PISARapaNui',
        'pages': 15,
        'type': 'arg'
    },
    10: {
        'name': 'Arg_PISACowsMilk',
        'pages': 14,
        'type': 'arg'
    },
    12: {
        'name': 'PopSci_Caveman',
        'pages': 9,
        'type': 'popsci'
    },
    1: {
        'name': 'PopSci_MultiplEYE',
        'pages': 12,
        'type': 'popsci'
    },
}

TOTAL_PAGES = sum([STIMULUS_ENCODING[id]['pages'] for id in STIMULUS_ENCODING])


def create_permutations() -> None:
    # create all possible permutations of the 11 stimuli by stimulus id that ranges from 3-13

    block_1 = [2, 5, 6, 7, 11]
    block_2 = [4, 8, 9, 10, 3, 12]

    all_perm_block_1 = len(list(itertools.permutations(block_1)))
    all_perm_block_2 = len(list(itertools.permutations(block_2)))

    stimuli_ids = [i for i in range(2, 13)]

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

        temp_version = (1,) + version
        pages = [STIMULUS_ENCODING[i]['pages'] for i in temp_version]

        _, is_break_allowed = is_break_time_allowed(pages)
        if is_break_allowed:
            equal_page_split.add(version)

        # check if the two longest stimuli are separated in before and after break
        if is_before_and_after_break(temp_version, 5, 8):
            two_long_separate.add(version)

        # two ins (ids 4 and 5) or two arg (ids 12 and 13) should not be consecutive
        if is_id_not_consecutive(temp_version, 2, 3):
            not_two_consecutive_ins.add(version)

        if is_id_not_consecutive(temp_version, 10, 11):
            not_two_consecutive_arg.add(version)

        # two longest stimuli should not be consecutive
        if is_id_not_consecutive(temp_version, 5, 8):
            two_long_not_consecutive.add(version)

    all_combined_two_long_separate = equal_page_split.intersection(two_long_separate).intersection(not_two_consecutive_ins).intersection(not_two_consecutive_arg)
    all_combined_two_long_not_consecutive = equal_page_split.intersection(two_long_not_consecutive).intersection(not_two_consecutive_ins).intersection(not_two_consecutive_arg)
    minimal_criteria = not_two_consecutive_arg.intersection(not_two_consecutive_ins)

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
    temp_perms = sorted(new_permutations.copy())
    final_permutations = []
    counts = [[0 for _ in range(11)] for _ in range(11)]
    max_count = 0
    found = 0

    with open('../final_permutations.txt', 'w', encoding='utf-8') as f:

        while len(final_permutations) < 200:
            print(f'Found: {len(final_permutations)}')
            for perm_index, perms in enumerate(temp_perms):
                # if all values in all list of count are equal to max count, then max_count += 1
                if all(max_count == c for count in counts for c in count):
                    max_count += 1
                    print(f'All stimuli appear now {max_count-1} times. Found: {found} permutations.')

                for position, stimulus_id in enumerate(perms):
                    # update the count for the stimulus id in that position
                    updated_count = counts[stimulus_id - 2][position] + 1
                    if updated_count > max_count:
                        break
                else:
                    if perms not in final_permutations:
                        found += 1
                        for i, stimulus_id in enumerate(perms):
                            counts[stimulus_id - 2][i] += 1

                        f.write(f'{perms}\n')
                        final_permutations.append(perms)


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
            if num_stimuli == 5 or num_stimuli == 6 or num_stimuli == 7:
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
