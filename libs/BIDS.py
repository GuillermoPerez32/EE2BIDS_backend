import os
from bids_validator import BIDSValidator


def validate(bids_directory):
    print('- Validate: init started.')
    file_paths = []
    result = []
    validator = BIDSValidator()
    for path, dirs, files in os.walk(bids_directory):
        for filename in files:
            if filename == '.bidsignore':
                continue

            if filename.endswith('_annotations.tsv'):
                continue

            if filename.endswith('_annotations.json'):
                continue

            temp = os.path.join(path, filename)
            file_paths.append(temp[len(bids_directory):len(temp)])
            result.append(validator.is_bids(temp[len(bids_directory):len(temp)]))
            # print(validator.is_bids(temp[len(bids_directory):len(temp)]))

    return file_paths, result
