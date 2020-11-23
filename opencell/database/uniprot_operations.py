import os
import re
import enum
import json
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell.database import models, utils, uniprot_utils


def insert_uniprot_metadata_from_id(session, uniprot_id, errors='warn'):
    '''
    Retrieve and insert Uniprot metadata for a given uniprot_id

    Note that we set limit=10 because the correct result for the query uniprot_id
    is sometimes not the top (i.e., first) result from the uniprotkb query
    '''
    metadata = uniprot_utils.query_uniprotkb(query=uniprot_id, only_reviewed=False, limit=10)
    if metadata is None:
        print('Warning: no UniprotKB results were found for uniprot_id %s' % uniprot_id)
        return

    # filter out results corresponding to other uniprot_ids
    # (this is necessary because we use limit=10 above, and because, sometimes,
    # one or more results are retrieved, but none of them actually match the query uniprot_id)
    metadata = metadata.loc[metadata.uniprot_id == uniprot_id]
    if not len(metadata):
        print(
            'Warning: UniprotKB results were retrieved for uniprot_id %s '
            'but none have the correct uniprot_id'
            % uniprot_id
        )
        return

    uniprot_metadata = models.UniprotMetadata(**metadata.iloc[0])
    utils.add_and_commit(session, uniprot_metadata, errors=errors)


def insert_uniprot_metadata_for_crispr_design(
    session, crispr_design_id, retrieved_metadata=None, errors='warn'
):
    '''
    Retrieve and insert the raw uniprot metadata for a crispr design

    Parameters
    ----------
    crispr_design_id : int, required
        the id of the crispr design for which to insert uniprot metadata
    retrieved_metadata : one-row pd.Dataframe, optional
        The raw uniprot metadata corresponding to the crispr design
        (intended for edge cases in which the correct metadata must be manually specified,
        rather than retrieved by uniprot_utils.get_uniprot_metadata)
    '''

    crispr_design = (
        session.query(models.CrisprDesign)
        .filter(models.CrisprDesign.id == crispr_design_id)
        .one()
    )

    if crispr_design.uniprot_id is not None:
        return

    # retrieve the metadata for the crispr design from the UniprotKB API
    if retrieved_metadata is None:

        # first try querying with the ENST ID, if one was provided
        if crispr_design.transcript_id is not None:
            retrieved_metadata = uniprot_utils.query_uniprotkb(
                query=crispr_design.transcript_id, limit=1
            )

        # if there is no ENST ID or no metadata was found, query with the target name
        if crispr_design.transcript_id is None or retrieved_metadata is None:
            print(
                "Warning: querying UniprotKB by target name and not by ENST ID for '%s'"
                % crispr_design.target_name
            )
            retrieved_metadata = uniprot_utils.query_uniprotkb(
                query=crispr_design.target_name, limit=1
            )

    if retrieved_metadata is None:
        print('Warning: no Uniprot metadata found for target %s' % crispr_design.target_name)
        return
    retrieved_metadata = retrieved_metadata.iloc[0]

    # check whether the retrieved metadata already exists
    extant_metadata = (
        session.query(models.UniprotMetadata)
        .filter(models.UniprotMetadata.uniprot_id == retrieved_metadata.uniprot_id)
        .one_or_none()
    )
    if extant_metadata is None:
        uniprot_metadata = models.UniprotMetadata(**retrieved_metadata)
        utils.add_and_commit(session, uniprot_metadata, errors=errors)

    # update the crispr design's uniprot_id
    crispr_design.uniprot_id = retrieved_metadata.uniprot_id
    utils.add_and_commit(session, crispr_design, errors=errors)


def insert_ensg_id(session, uniprot_id):
    '''
    Retrieve and insert the ENSG ID in the uniprot_metadata table for a given uniprot_id
    (using the Uniprot mapper API to look up the ENSG ID)
    '''

    uniprot_metadata = (
        session.query(models.UniprotMetadata)
        .filter(models.UniprotMetadata.uniprot_id == uniprot_id)
        .one_or_none()
    )

    if uniprot_metadata is None:
        print('Warning: no uniprot metadata found for uniprot_id %s' % uniprot_id)
        return

    # try to look up the ensg_id using mygene
    try:
        ensg_id = uniprot_utils.map_uniprot_to_ensg_using_mygene(uniprot_id)
    except Exception:
        print('Uncaught error in mygene API query for uniprot_id %s' % uniprot_id)
        return

    # if mygene didn't work, try using the uniprot mapper API
    # (because there are, rarely, ids that are not in mygene but are in the Uniprot mapper API)
    if ensg_id is None:
        try:
            ensg_id = uniprot_utils.map_uniprot_to_ensg_using_uniprot(uniprot_id)
        except Exception:
            print('Uncaught error in uniprot mapper query for uniprot_id %s' % uniprot_id)
            return

    if ensg_id is None:
        print('Warning: no ENSG ID found for uniprot_id %s' % uniprot_id)
        return

    uniprot_metadata.ensg_id = ensg_id
    utils.add_and_commit(session, uniprot_metadata, errors='warn')
