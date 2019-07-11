
# polyclonallines GET

{
    "cell_line_id": 2, 
    "well_id": "A02",
    "plate_design_id": "P0005", 
    "plate_instance_id": 5, 

    "target_family": "actin", 
    "target_name": "ACTB", 
    "target_terminus": "N_TERMINUS", 
    "terminus_notes": "Allen collection", 
    "transcript_id": "ENST00000331789", 
    "transcript_notes": None, 

    "electroporation_date": "Tue, 16 Oct 2018 00:00:00 GMT", 

    "protospacer_name": "pl5_crRNA_A2_ACTB", 
    "protospacer_notes": "cuts close to intron/exon junction", 
    "protospacer_sequence": "GCTATTCTCGCAGCTCACCA", 
    "template_name": "pl5_mNG11_A2_ACTB", 
    "template_notes": None, 
    "template_sequence": "", 

    "facs": {
        "properties": {
            "grade": "A",

            # the area and intensity of the putative GFP positive population
            # (this is the right-hand 'side' of the FITC distribution,
            # identified by subtracting the fitted negative-control distribution)
            "gfp_area": 1,
            "gfp_linear_intensity": 100,
            "gfp_log_intensity": 2,
        },
        "histograms": {
            "bin_edges": [0, 10, 20],

            # raw counts from the (gated and hlog-transformed) FACS data
            # (nb it seems safer to preserve the counts here and do the normalization on the client)
            "sample_counts": [0, 0, .5],
            "control_counts": [0, 1, 0],

            # offset and scale obtained by fitting the control distribution
            # to the GFP-negative 'part' (the left-hand 'side') of the sample distribution
            # TODO: are these relative to the raw counts or the density?
            "control_offset": 200,
            "control_scale": .95 
        }
    },

    # list of image data, one for each FOV
    "images": [
        {
            # dataset_id for retrieving the full image/stack
            'dataset_id': 1,
            # thumbnail preview as base64-encoded string
            'thumbnail': '',
        }
    ],

    "sequencing": {
        # TODO!
    }
  }

