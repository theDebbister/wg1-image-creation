def check_stimulus_types(stimulus_types: list) -> None:

    if not len(stimulus_types) == 2:
        raise ValueError(f'Only two stimulus types are allowed (practice and experiment), '
                         f'but {len(stimulus_types)} were found. Please check the stimulus types in the excel files.')
    else:
        if 'practice' not in stimulus_types or 'experiment' not in stimulus_types:
            raise ValueError(f'Only two stimulus types are allowed (practice and experiment), '
                             f'but {stimulus_types} were found. Please check the stimulus types in the excel files.')
