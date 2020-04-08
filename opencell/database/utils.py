import re
import json
import datetime


def url_from_credentials(credentials_filepath):
    '''
    Generate database URL from credentials in a JSON file
    '''

    with open(credentials_filepath) as file:
        credentials = json.load(file)

    url = '{driver}://{username}:{password}@{host}:{port}/{dbname}'
    return url.format(**credentials)


def format_well_id(well_id):
    '''
    Zero-pad well_ids like 'A1' to 'A01'
    '''
    if re.match('^[A-H][1-9]$', well_id):
        row, column = well_id
        well_id = '%s0%s' % (row, column)
    return well_id


def format_plate_design_id(design_id):
    '''
    Format a plate design id if it's not already in the format required by the database
    This format is: `'P%04d' % plate_number`

    For convenience, this method is relatively permissive.

    All of the following examples will yield 'P0001':
    'Plate 1, 'plate1', 'plate01', '01', 1

    '''

    design_id = str(design_id)

    result = re.match('^P[0-9]{4}$', design_id)
    if result is None:
        plate_number = None

        # the design_id either begins with 'plate' or is the plate_number itself
        result = re.match('^p?(?:late)? ?([0-9]+)$', design_id.lower())
        if result:
            plate_number = result.groups()[0]
        else:
            plate_number = design_id

        try:
            plate_number = int(plate_number)
        except ValueError:
            raise ValueError("'%s' is not a valid design_id" % design_id)

        design_id = ('P%04d' % plate_number)
    return design_id


def is_sequence(sequence):
    alphabet = set(['a', 't', 'g', 'c'])
    return set(sequence.lower()).issubset(alphabet)


def current_date():
    return datetime.datetime.now().strftime('%Y-%m-%d')
