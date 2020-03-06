import re
import datetime

def format_ms_plate(plate_id):
    """
    Format Ms Plates to 'CZBMPI_%04d' % plate_number
    Also allow for 'CZBMPI%04d.d format

    """
    plate_id = str(plate_id)

    result = re.match('^CZBMPI_[0-9]{4}(.[0-9])?$', plate_id)
    if result is None:
        sub_plate = None
        plate_number = None

        # If the plate ends with subheading such as 0009.2, denoted by the
        # decimal, save the decimal
        sub_result = re.search(r'(.[0-9]+$)', plate_id)
        if sub_result:
            sub_plate = sub_result.groups()[0]

        # Check for plate numbering
        result = re.search(r'([0-9]+)', plate_id)
        if result:
            plate_number = result.groups()[0]

        try:
            plate_number = int(plate_number)
        except:
            # plate_number = 9999
            raise ValueError("'%s' is not a valid plate_id" % plate_id)

        plate_id = ('CZBMPI_%04d' % plate_number)
        if sub_plate:
            if sub_plate != '.0':
                plate_id = plate_id + sub_plate

    return plate_id

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
        result = re.search('([0-9]+)$', design_id.lower())
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
