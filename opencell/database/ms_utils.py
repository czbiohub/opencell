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
