"""
This file contains any code that is necessary to generate the images, randomization etc. for the MultiplEYE Aging Corpus.
"""
import pandas as pd


def get_stimulus_randomization_orders(original_versions: pd.DataFrame):
    """
    The aging subcorpus only uses these stimuli:
        2   Ins_HumanRights
        4   Lit_Alchemist
        10  Arg_PISACowsMilk
        12  PopSci_Caveman
        13  Enc_WikiMoon
        7   Lit_NorthWind
    The order version will be cleaned from those stimuli. Duplicates can then be removed.
    """

    used_stimulus_ids = {2, 4, 10, 12, 13, 7}
    trial_cols = [f'trial_{i}' for i in range(1, 13)]
    output_cols = ['version_number', 'participant_id', 'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5', 'trial_6']

    cleaned_rows = []
    for _, row in original_versions.iterrows():
        kept = [int(row[col]) for col in trial_cols if row[col] in used_stimulus_ids]
        new_row = {
            'version_number': int(row['version_number']),
            'participant_id': row['participant_id'],
        }
        for i, stimulus_id in enumerate(kept, start=1):
            new_row[f'trial_{i}'] = stimulus_id
        cleaned_rows.append(new_row)

    trial_output_cols = ['trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5', 'trial_6']
    result = pd.DataFrame(cleaned_rows, columns=output_cols).drop_duplicates(subset=trial_output_cols).reset_index(drop=True)
    result['version_number'] = result.index + 1
    return result
