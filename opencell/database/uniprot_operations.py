import os
import re
import enum
import json
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell.database import models, utils, uniprot_utils

import logging
logger = logging.getLogger(__name__)


def insert_uniprot_metadata_from_id(session, uniprot_id):
    '''
    Retrieve and insert Uniprot metadata for a given uniprot_id

    Note that we set limit=10 because the correct result for the query uniprot_id
    is sometimes not the top (i.e., first) result from the uniprotkb query
    '''
    metadata = uniprot_utils.query_uniprotkb(query=uniprot_id, only_reviewed=False, limit=10)
    if metadata is None:
        logger.warning('No UniprotKB results were found for uniprot_id %s' % uniprot_id)
        return

    # filter out results corresponding to other uniprot_ids
    # (this is necessary because we use limit=10 above, and because, sometimes,
    # one or more results are retrieved, but none of them actually match the query uniprot_id)
    metadata = metadata.loc[metadata.uniprot_id == uniprot_id]
    if not len(metadata):
        logger.warning(
            'UniprotKB results were retrieved for uniprot_id %s '
            'but none have the correct uniprot_id'
            % uniprot_id
        )
        return

    uniprot_metadata = models.UniprotMetadata(**metadata.iloc[0])
    utils.add_and_commit(session, uniprot_metadata)


def insert_uniprot_metadata_for_crispr_design(session, crispr_design_id, retrieved_metadata=None):
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
            logger.warning(
                "Querying UniprotKB by target name and not by ENST ID for '%s'"
                % crispr_design.target_name
            )
            retrieved_metadata = uniprot_utils.query_uniprotkb(
                query=crispr_design.target_name, limit=1
            )

    if retrieved_metadata is None:
        logger.warning('No Uniprot metadata found for target %s' % crispr_design.target_name)
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
        utils.add_and_commit(session, uniprot_metadata)

    # update the crispr design's uniprot_id
    crispr_design.uniprot_id = retrieved_metadata.uniprot_id
    utils.add_and_commit(session, crispr_design)


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
        logger.warning('No uniprot metadata found for uniprot_id %s' % uniprot_id)
        return

    # try to look up the ensg_id using mygene
    try:
        ensg_id = uniprot_utils.map_uniprot_to_ensg_using_mygene(uniprot_id)
    except Exception:
        logger.error('Uncaught error in mygene API query for uniprot_id %s' % uniprot_id)
        return

    # if mygene didn't work, try using the uniprot mapper API
    # (because there are, rarely, ids that are not in mygene but are in the Uniprot mapper API)
    if ensg_id is None:
        try:
            ensg_id = uniprot_utils.map_uniprot_to_ensg_using_uniprot(uniprot_id)
        except Exception:
            logger.error('Uncaught error in uniprot mapper query for uniprot_id %s' % uniprot_id)
            return

    if ensg_id is None:
        logger.warning('No ENSG ID found for uniprot_id %s' % uniprot_id)
        return

    uniprot_metadata.ensg_id = ensg_id
    utils.add_and_commit(session, uniprot_metadata)


def generate_protein_group_uniprot_metadata_associations(Session):
    '''
    Populate the association table between the mass_spec_protein_group table
    and the uniprot_metadata table, using uniprot_ids.

    The 'raw' uniprot_ids are found in the uniprot_ids column of the protein_group table;
    here, these are parsed to eliminate isoform-specific ids and also ids
    for which no cached uniprot metadata exists (these are rare).

    Note that, when new mass spec protein groups are inserted, it is important
    to first update the cached uniprot_metadata using `insert_uniprot_metadata_for_protein_groups`,
    and only then use this method to rebuild the association table.
    '''

    engine = Session.get_bind()
    logger.info('Truncating the protein_group_uniprot_metadata_association table')
    engine.execute('truncate protein_group_uniprot_metadata_association')

    uniprot_metadata = uniprot_utils.export_uniprot_metadata(engine)
    logger.info('Found metadata for %s uniprot_ids' % uniprot_metadata.shape[0])

    # all (protein_group_id, uniprot_id) pairs
    group_uniprot_ids = pd.read_sql(
        '''
        select id as protein_group_id, unnest(uniprot_ids) as uniprot_id
        from mass_spec_protein_group;
        ''',
        engine
    )

    # drop isoform-specific uniprot_ids
    group_uniprot_ids['uniprot_id'] = group_uniprot_ids.uniprot_id.apply(lambda s: s.split('-')[0])

    # merge uniprot metadata on uniprot_id to get the (group_id, ensg_id) associations
    group_ensg_ids = pd.merge(uniprot_metadata, group_uniprot_ids, on='uniprot_id', how='inner')
    group_ensg_ids = group_ensg_ids.groupby(['protein_group_id', 'ensg_id']).first().reset_index()
    logger.info('Found %s (protein_group_id, ensg_id) pairs' % group_ensg_ids.shape[0])

    # merge reference uniprot_ids on ensg_id to get the final (group_id, uniprot_id) associations
    group_consensus_ids = pd.merge(
        group_ensg_ids[['protein_group_id', 'ensg_id']],
        uniprot_metadata.loc[uniprot_metadata.is_reference],
        on='ensg_id',
        how='inner'
    )

    rows = [
        dict(protein_group_id=row.protein_group_id, uniprot_id=row.uniprot_id)
        for ind, row in group_consensus_ids.iterrows()
    ]

    logger.info(
        'Inserting %s rows into the protein_group_uniprot_metadata_association table'
        % len(rows)
    )
    Session.bulk_insert_mappings(models.ProteinGroupUniprotMetadataAssociation, rows)
    Session.commit()


def generate_protein_group_crispr_design_associations(Session):
    '''
    Populate the association table between mass_spec_protein_group table
    and the crispr_design table using the ENSG IDs cached in the uniprot_metadata table

    Background
    ----------
    Each crispr_design is always associated with one uniprot_id and therefore one ensg_id,
    while each protein_group consists of many uniprot_ids, which may be associated
    with more than one unique ensg_id (though often only one).

    Also, there is more than one crispr_design associated with some ensg_ids.

    Note that, when new protein_groups are inserted, it is necessary
    to first update the cached ensg_ids using `insert_ensg_ids`,
    and only then call this method to rebuild the associations.
    '''

    engine = Session.get_bind()
    logger.info('Truncating the protein_group_crispr_design_association table')
    engine.execute('truncate protein_group_crispr_design_association')

    # all crispr designs for which uniprot_metadata exists
    crispr_designs = pd.read_sql(
        '''select * from crispr_design inner join uniprot_metadata using (uniprot_id)''',
        engine
    )
    logger.info('Found %s crispr designs' % crispr_designs.shape[0])

    # all mass spec protein groups
    groups = (
        Session.query(models.MassSpecProteinGroup)
        .options(
            db.orm.joinedload(models.MassSpecProteinGroup.uniprot_metadata)
        )
        .all()
    )
    logger.info('Found %s protein groups' % len(groups))

    # find the crispr_designs whose ENSG IDs appear in each group's ENSG IDs
    assocs = []
    for group in groups:
        ensg_ids = [d.ensg_id for d in group.uniprot_metadata]
        crispr_design_ids = crispr_designs.loc[crispr_designs.ensg_id.isin(ensg_ids)].id.tolist()
        assocs.extend([
            dict(crispr_design_id=crispr_design_id, protein_group_id=group.id)
            for crispr_design_id in crispr_design_ids
        ])

    logger.info('Inserting %s (protein_group, crispr_design) associations' % len(assocs))
    Session.bulk_insert_mappings(models.ProteinGroupCrisprDesignAssociation, assocs)
    Session.commit()
