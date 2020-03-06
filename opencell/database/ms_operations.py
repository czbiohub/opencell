import os
import re
import enum
import json
import numpy as np
import pandas as pd
import sqlalchemy as db

from contextlib import contextmanager
from opencell.database import operations
from opencell.database import models
from opencell.database import ms_models
from opencell.imaging import processors
from opencell import constants


class PulldownOperations:
    '''
    '''

    def __init__(self, line):
        self.line = line

    @classmethod
    def from_plate_well(cls, session, design_id, well_id):
        '''
        Convenience method to retrieve the cell line corresponding to a plate design and a well id,
        *assuming* that there is only one electroporation per one instance of the pulldown.
        '''

        lines = (
            session.query(ms_models.CellLine)
            .join(ms_models.Electroporation)
            .join(ms_models.PlateInstance)
            .join(ms_models.PlateDesign)
            .join(ms_models.CrisprDesign)
            .filter(ms_models.PlateInstance.plate_design_id == design_id)
            .filter(ms_models.CrisprDesign.well_id == well_id)
            .all()
        )
        if len(lines) > 1:
            raise ValueError('More than one line found for well %s of plate %s' % (well_id, design_id))
        if not lines:
            raise ValueError('No line found for well %s of plate %s' % (well_id, design_id))

        return cls(lines[0])


    @classmethod
    def from_target_name(cls, session, target_name):
        '''
        Convenience method to retrieve the cell line for the given target_name
        If there is more than one cell_line for the target_name,
        then the PolyClonalLineOperations class is instantiated using the first such cell_line
        '''
        cds = (
            session.query(ms_models.CrisprDesign)
            .filter(db.func.lower(ms_models.CrisprDesign.target_name) == db.func.lower(target_name))
            .all()
        )

        if len(cds) > 1:
            print('Warning: %s cell lines found for target %s' % (len(cds), target_name))
        if len(cds) == 0:
            raise ValueError('No cells lines found for target %s' % target_name)

        cd = cds[0]
        return cls.from_plate_well(session, cd.plate_design_id, cd.well_id)

    def insert_pulldown_row(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown data """

        # drop any existing data
        if self.line.pulldown:
            operations.delete_and_commit(session, self.line.pulldown)

        pulldown_data = ms_models.Pulldown(
            cell_line=self.line,
            replicate=row.replicate,
            pulldown_plate_id=row.pulldown_plate_id,
            pulldown_well_id=row.pulldown_well_id)
        operations.add_and_commit(session, pulldown_data, errors=errors)
