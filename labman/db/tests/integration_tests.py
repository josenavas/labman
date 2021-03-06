#!/usr/bin/env python

from datetime import datetime
from itertools import chain
import re

import numpy as np
import click

from labman.db.process import (
    SamplePlatingProcess, GDNAExtractionProcess, GDNAPlateCompressionProcess,
    LibraryPrep16SProcess, NormalizationProcess, QuantificationProcess,
    LibraryPrepShotgunProcess, PoolingProcess, SequencingProcess)
from labman.db.user import User
from labman.db.plate import PlateConfiguration, Plate
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition
from labman.db.sql_connection import TRN


def get_samples():
    with TRN:
        TRN.add("SELECT sample_id FROM qiita.study_sample")
        return TRN.execute_fetchflatten()


def create_sample_plate_process(user, samples):
    plate_config = PlateConfiguration(1)
    num_rows = plate_config.num_rows
    num_cols = plate_config.num_columns
    sp_process = SamplePlatingProcess.create(
        user, plate_config, 'Test plate %s' % datetime.now())

    # Plate the samples
    for idx, sample in enumerate(samples):
        i = int(idx / num_cols) + 1
        j = (idx % num_cols) + 1

        # Make sure that the user didn't pass more samples than wells
        if i > num_rows:
            break

        sp_process.update_well(i, j, sample)

    sample_plate = sp_process.plate
    return sp_process, sample_plate


def create_gdna_extraction_process(user, plate):
    kingfisher = Equipment(11)
    epmotion = Equipment(6)
    epmotion_tool = Equipment(15)
    extraction_kit = ReagentComposition(1)
    ext_process = GDNAExtractionProcess.create(
        user, plate, kingfisher, epmotion, epmotion_tool, extraction_kit, 100,
        'GDNA test plate %s' % datetime.now())
    gdna_plate = ext_process.plates[0]
    return ext_process, gdna_plate


def create_amplicon_prep(user, plate):
    primer_plate = Plate(11)
    epmotion = Equipment(6)
    master_mix = ReagentComposition(2)
    water_lot = ReagentComposition(3)
    epmotion_tool_tm300 = Equipment(16)
    epmotion_tool_tm50 = Equipment(17)
    amplicon_process = LibraryPrep16SProcess.create(
        user, plate, primer_plate, 'Amplicon test plate %s' % datetime.now(),
        epmotion, epmotion_tool_tm300, epmotion_tool_tm50, master_mix,
        water_lot, 75,)
    amplicon_plate = amplicon_process.plates[0]
    return amplicon_process, amplicon_plate


def create_compression_process(user, gdna_plates):
    comp_process = GDNAPlateCompressionProcess.create(
        user, gdna_plates, 'Compressed test plate %s' % datetime.now(),
        Equipment(6))
    compressed_plate = comp_process.plates[0]
    return comp_process, compressed_plate


def create_quantification_process(user, plate):
    plate_config = plate.plate_configuration
    concentrations = np.around(
        np.random.rand(plate_config.num_rows, plate_config.num_columns), 6)
    quant_process = QuantificationProcess.create(user, plate, concentrations)
    return quant_process


def create_pool_quantification_process(user, pools):
    concentrations = np.around(np.random.rand(len(pools)), 6)
    concentrations = [{'composition': p, 'concentration': c}
                      for p, c in zip(pools, concentrations)]
    return QuantificationProcess.create_manual(user, concentrations)


def create_normalization_process(user, quant_process):
    water = ReagentComposition(3)
    norm_process = NormalizationProcess.create(
        user, quant_process, water,
        'Normalized test plate %s' % datetime.now())
    norm_plate = norm_process.plates[0]
    return norm_process, norm_plate


def create_shotgun_process(user, norm_plate):
    kappa = ReagentComposition(4)
    stub = ReagentComposition(5)
    shotgun_process = LibraryPrepShotgunProcess.create(
        user, norm_plate, 'Test Shotgun Library %s' % datetime.now(), kappa,
        stub, 4000, Plate(19), Plate(20))
    shotgun_plate = shotgun_process.plates[0]
    return shotgun_process, shotgun_plate


def create_plate_pool_process(user, quant_process, plate, func_data):
    input_compositions = []
    echo = Equipment(8)
    for well in chain.from_iterable(plate.layout):
        if well is not None:
            input_compositions.append({
                'composition': well.composition, 'input_volume': 1,
                'percentage_of_output': 1/9.0})
    pool_process = PoolingProcess.create(
        user, quant_process, 'New test pool name %s' % datetime.now(),
        4, input_compositions, func_data, robot=echo)
    return pool_process


def create_pools_pool_process(user, quant_process, pools):
    input_compositions = [
        {'composition': p, 'input_volume': 1, 'percentage_of_output': 1/9.0}
        for p in pools]
    pool_process = PoolingProcess.create(
        user, quant_process, 'New pool name %s' % datetime.now(), 5,
        input_compositions, {"function": "amplicon_pool", "parameters": {}})
    return pool_process


def create_sequencing_process(user, pools):
    seq_process = SequencingProcess.create(
        user, pools, 'New sequencing run %s' % datetime.now(),
        'Run experiment %s' % datetime.now(), Equipment(18), 151, 151,
        User('admin@foo.bar'),
        contacts=[User('test@foo.bar'), User('demo@microbio.me')])
    return seq_process


def amplicon_workflow(user, samples):
    # Sample Plating
    sp_process, sample_plate = create_sample_plate_process(user, samples[:96])
    # gDNA extraction
    ext_process, gdna_plate = create_gdna_extraction_process(
        user, sample_plate)
    # Amplicon library prep
    amplicon_process, amplicon_plate = create_amplicon_prep(user, gdna_plate)
    # Library plate quantification
    amplicon_quant_process = create_quantification_process(
        user, amplicon_plate)
    # Plate pooling process
    plate_pool_process = create_plate_pool_process(
        user, amplicon_quant_process, amplicon_plate,
        {'function': 'amplicon',
         'parameters': {"dna_amount": 240, "min_val": 1, "max_val": 15,
                        "blank_volume": 2, "robot": 6, "destination": 1}})
    # Quantify pools
    pool_quant_process = create_pool_quantification_process(
        user, [plate_pool_process.pool])
    # Create sequencing pool process
    seq_pool_process = create_pools_pool_process(
        user, pool_quant_process, [plate_pool_process.pool])
    # Sequencing process
    seq_process = create_sequencing_process(user, [seq_pool_process.pool])
    return seq_process


def shotgun_workflow(user, samples):
    # Sample Plating
    sp_process, sample_plate = create_sample_plate_process(user, samples[:96])
    # gDNA extraction
    ext_process, gdna_plate = create_gdna_extraction_process(
        user, sample_plate)
    # gDNA compression
    comp_process, compressed_plate = create_compression_process(
        user, [gdna_plate])
    # gDNA compressed quantification
    gdna_comp_quant_process = create_quantification_process(
        user, compressed_plate)
    # Normalization process
    norm_process, norm_plate = create_normalization_process(
        user, gdna_comp_quant_process)
    # Library prep shotgun
    shotgun_process, shotgun_plate = create_shotgun_process(user, norm_plate)
    # Quantify library plate
    shotgun_quant_process = create_quantification_process(user, shotgun_plate)
    # Pooling process
    pool_process = create_plate_pool_process(
        user, shotgun_quant_process, shotgun_plate,
        {'function': 'equal', 'parameters': {'total_vol': 60, 'size': 500}})
    # Sequencing process
    seq_process = create_sequencing_process(user, [pool_process.pool])
    return seq_process


@click.command()
def integration_tests():
    samples = get_samples()
    user = User('test@foo.bar')
    amplicon_seq_process = amplicon_workflow(user, samples)
    shotgun_seq_process = shotgun_workflow(user, samples)

    obs = amplicon_seq_process.generate_sample_sheet()
    res = re.match(EXP_AMPLICON_SAMPLE_SHEET, obs)
    if res is None:
        raise ValueError(
            'Amplicon sample sheet does not match expected regex:\n%s' % obs)

    obs = shotgun_seq_process.generate_sample_sheet()
    res = re.match(EXP_SHOTGUN_SAMPLE_SHEET, obs)
    if res is None:
        raise ValueError(
            'Shotgun sample sheet does not match expected regex:\n%s' % obs)


EXP_AMPLICON_SAMPLE_SHEET = r"""# PI,Admin,admin@foo.bar
# Contact,Demo,Dude
# Contact emails,demo@microbio.me,test@foo.bar
\[Header\]
IEMFileVersion,4
Investigator Name,Admin
Experiment Name,Run experiment \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}
Date,\d{4}-\d{2}-\d{2}
Workflow,GenerateFASTQ
Application,FASTQ Only
Assay,Amplicon
Description,
Chemistry,Default

\[Reads\]
151
151

\[Settings\]
ReverseComplement,0

\[Data\]
Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,,
New_sequencing_run_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2}_\d{6},,,,,NNNNNNNNNNNN,,,,,"""  # noqa


EXP_SHOTGUN_SAMPLE_SHEET = r"""# PI,Admin,admin@foo.bar
# Contact,Demo,Dude
# Contact emails,demo@microbio.me,test@foo.bar
\[Header\]
IEMFileVersion,4
Investigator Name,Admin
Experiment Name,Run experiment \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}
Date,\d{4}-\d{2}-\d{2}
Workflow,GenerateFASTQ
Application,FASTQ Only
Assay,Metagenomics
Description,
Chemistry,Default

\[Reads\]
151
151

\[Settings\]
ReverseComplement,0

\[Data\]
Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
1,1_SKB1_640202,1_SKB1_640202,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A23,iTru7_101_09,TGTACACC,iTru5_08_A,CATCTGCT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB1.640202
1,1_SKB2_640194,1_SKB2_640194,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A17,iTru7_101_06,AACAACCG,iTru5_05_A,GGTACGAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB2.640194
1,1_SKB3_640195,1_SKB3_640195,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E1,iTru7_102_10,GTTAAGGC,iTru5_09_B,ACGGACTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB3.640195
1,1_SKB4_640189,1_SKB4_640189,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C17,iTru7_102_06,TGTGCGTT,iTru5_05_B,AAGCATCG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB4.640189
1,1_SKB5_640181,1_SKB5_640181,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A13,iTru7_101_04,GATCCATG,iTru5_03_A,AACACCAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB5.640181
1,1_SKB6_640176,1_SKB6_640176,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E3,iTru7_102_11,AAGCCACA,iTru5_10_B,CATGTGTG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB6.640176
1,1_SKB7_640196,1_SKB7_640196,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A5,iTru7_115_11,CTTAGGAC,iTru5_123_H,CTCTTGTC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB7.640196
1,1_SKB8_640193,1_SKB8_640193,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A1,iTru7_115_09,AGCACTTC,iTru5_121_H,GATGCTAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB8.640193
1,1_SKB9_640200,1_SKB9_640200,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C9,iTru7_102_02,CTTACCTG,iTru5_01_B,AGTGGCAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKB9.640200
1,1_SKD1_640179,1_SKD1_640179,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C1,iTru7_101_10,GTATGCTG,iTru5_09_A,CTCTCAGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD1.640179
1,1_SKD2_640178,1_SKD2_640178,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A19,iTru7_101_07,ACTCGTTG,iTru5_06_A,CGATCGAT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD2.640178
1,1_SKD3_640198,1_SKD3_640198,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C3,iTru7_101_11,TGATGTCC,iTru5_10_A,TCGTCTGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD3.640198
1,1_SKD4_640185,1_SKD4_640185,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C23,iTru7_102_09,ACAGCTCA,iTru5_08_B,ACCTCTTC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD4.640185
1,1_SKD5_640186,1_SKD5_640186,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C11,iTru7_102_03,CGTTGCAA,iTru5_02_B,GTGGTATG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD5.640186
1,1_SKD6_640190,1_SKD6_640190,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A15,iTru7_101_05,GCCTATCA,iTru5_04_A,CGTATCTC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD6.640190
1,1_SKD7_640191,1_SKD7_640191,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C19,iTru7_102_07,TAGTTGCG,iTru5_06_B,TACTCCAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD7.640191
1,1_SKD8_640184,1_SKD8_640184,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A3,iTru7_115_10,GCATACAG,iTru5_122_H,GAACGGTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD8.640184
1,1_SKD9_640182,1_SKD9_640182,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C15,iTru7_102_05,TCACGTTC,iTru5_04_B,CGTCAAGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKD9.640182
1,1_SKM1_640183,1_SKM1_640183,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E5,iTru7_102_12,ACACGGTT,iTru5_11_B,TGCCTCAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM1.640183
1,1_SKM2_640199,1_SKM2_640199,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C7,iTru7_102_01,ATAAGGCG,iTru5_12_A,CATTCGTC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM2.640199
1,1_SKM3_640197,1_SKM3_640197,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C13,iTru7_102_04,GATTCAGC,iTru5_03_B,TGAGCTGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM3.640197
1,1_SKM4_640180,1_SKM4_640180,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A9,iTru7_101_02,CTGTGTTG,iTru5_01_A,ACCGACAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM4.640180
1,1_SKM5_640177,1_SKM5_640177,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A11,iTru7_101_03,TGAGGTGT,iTru5_02_A,CTTCGCAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM5.640177
1,1_SKM6_640187,1_SKM6_640187,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C21,iTru7_102_08,AAGAGCCA,iTru5_07_B,GATACCTG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM6.640187
1,1_SKM7_640188,1_SKM7_640188,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A21,iTru7_101_08,CCTATGGT,iTru5_07_A,AAGACACC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM7.640188
1,1_SKM8_640201,1_SKM8_640201,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},C5,iTru7_101_12,GTCCTTCT,iTru5_11_A,CAATAGCC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM8.640201
1,1_SKM9_640192,1_SKM9_640192,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},A7,iTru7_211_01,GCTTCTTG,iTru5_124_H,AACGCCTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},1.SKM9.640192
1,blank_30_C10,blank_30_C10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E19,iTru7_103_07,TGTGACTG,iTru5_06_C,AGCTACCA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C10
1,blank_30_C11,blank_30_C11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E21,iTru7_103_08,CGAAGAAC,iTru5_07_C,AACCGAAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C11
1,blank_30_C12,blank_30_C12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E23,iTru7_103_09,GGTGTCTT,iTru5_08_C,ATCGCAAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C12
1,blank_30_C4,blank_30_C4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E7,iTru7_103_01,CAGCGATT,iTru5_12_B,ATCTGACC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C4
1,blank_30_C5,blank_30_C5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E9,iTru7_103_02,TAGTGACC,iTru5_01_C,CACAGACT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C5
1,blank_30_C6,blank_30_C6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E11,iTru7_103_03,CGAGACTA,iTru5_02_C,CACTGTAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C6
1,blank_30_C7,blank_30_C7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E13,iTru7_103_04,GACATGGT,iTru5_03_C,CACAGGAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C7
1,blank_30_C8,blank_30_C8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E15,iTru7_103_05,GCATGTCT,iTru5_04_C,CCATGAAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C8
1,blank_30_C9,blank_30_C9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},E17,iTru7_103_06,ACTCCATC,iTru5_05_C,GCCAATAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.C9
1,blank_30_D1,blank_30_D1,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G1,iTru7_103_10,AAGAAGGC,iTru5_09_C,GTTGCTGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D1
1,blank_30_D10,blank_30_D10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G19,iTru7_104_07,TTAGGTCG,iTru5_06_D,TCGACAAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D10
1,blank_30_D11,blank_30_D11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G21,iTru7_104_08,GCAAGATC,iTru5_07_D,GCTGAATC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D11
1,blank_30_D12,blank_30_D12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G23,iTru7_104_09,AGAGCCTT,iTru5_08_D,AGTTGTGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D12
1,blank_30_D2,blank_30_D2,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G3,iTru7_103_11,AGGTTCGA,iTru5_10_C,TCTAGTCC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D2
1,blank_30_D3,blank_30_D3,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G5,iTru7_103_12,CATGTTCC,iTru5_11_C,GACGAACT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D3
1,blank_30_D4,blank_30_D4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G7,iTru7_104_01,GTGCCATA,iTru5_12_C,TTCGTACG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D4
1,blank_30_D5,blank_30_D5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G9,iTru7_104_02,CCTTGTAG,iTru5_01_D,CGACACTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D5
1,blank_30_D6,blank_30_D6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G11,iTru7_104_03,GCTGGATT,iTru5_02_D,AGACGCTA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D6
1,blank_30_D7,blank_30_D7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G13,iTru7_104_04,TAACGAGG,iTru5_03_D,TGACAACC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D7
1,blank_30_D8,blank_30_D8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G15,iTru7_104_05,ATGGTTGC,iTru5_04_D,GGTACTTC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D8
1,blank_30_D9,blank_30_D9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},G17,iTru7_104_06,CCTATACC,iTru5_05_D,CTGTATGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.D9
1,blank_30_E1,blank_30_E1,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I1,iTru7_104_10,GCAATGGA,iTru5_09_D,TGTCGACT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E1
1,blank_30_E10,blank_30_E10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I19,iTru7_105_07,TGGCATGT,iTru5_06_E,TATGACCG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E10
1,blank_30_E11,blank_30_E11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I21,iTru7_105_08,AGAAGCGT,iTru5_07_E,AGCTAGTG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E11
1,blank_30_E12,blank_30_E12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I23,iTru7_105_09,AGCGGAAT,iTru5_08_E,GAACGAAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E12
1,blank_30_E2,blank_30_E2,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I3,iTru7_104_11,CTGGAGTA,iTru5_10_D,AAGGCTCT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E2
1,blank_30_E3,blank_30_E3,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I5,iTru7_104_12,GAACATCG,iTru5_11_D,CCTAACAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E3
1,blank_30_E4,blank_30_E4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I7,iTru7_105_01,GCACAACT,iTru5_12_D,AAGACGAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E4
1,blank_30_E5,blank_30_E5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I9,iTru7_105_02,TTCTCTCG,iTru5_01_E,GACTTGTG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E5
1,blank_30_E6,blank_30_E6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I11,iTru7_105_03,AACGGTCA,iTru5_02_E,CAACTCCA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E6
1,blank_30_E7,blank_30_E7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I13,iTru7_105_04,ACAGACCT,iTru5_03_E,TGTTCCGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E7
1,blank_30_E8,blank_30_E8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I15,iTru7_105_05,TCTCTTCC,iTru5_04_E,ACCGCTAT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E8
1,blank_30_E9,blank_30_E9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},I17,iTru7_105_06,AGTGTTGG,iTru5_05_E,CTTAGGAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.E9
1,blank_30_F1,blank_30_F1,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K1,iTru7_105_10,TAACCGGT,iTru5_09_E,CGTCTAAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F1
1,blank_30_F10,blank_30_F10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K19,iTru7_106_07,CGTCTTGT,iTru5_06_F,AGCCAACT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F10
1,blank_30_F11,blank_30_F11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K21,iTru7_106_08,CGTGATCA,iTru5_07_F,CTAGCTCA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F11
1,blank_30_F12,blank_30_F12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K23,iTru7_106_09,CCAAGTTG,iTru5_08_F,GGAAGAGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F12
1,blank_30_F2,blank_30_F2,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K3,iTru7_105_11,CATGGAAC,iTru5_10_E,AACCAGAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F2
1,blank_30_F3,blank_30_F3,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K5,iTru7_105_12,ATGGTCCA,iTru5_11_E,CGCCTTAT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F3
1,blank_30_F4,blank_30_F4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K7,iTru7_106_01,CTTCTGAG,iTru5_12_E,CTCGTTCT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F4
1,blank_30_F5,blank_30_F5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K9,iTru7_106_02,AACCGAAG,iTru5_01_F,GTGAGACT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F5
1,blank_30_F6,blank_30_F6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K11,iTru7_106_03,TTCGTACC,iTru5_02_F,AACACGCT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F6
1,blank_30_F7,blank_30_F7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K13,iTru7_106_04,CTGTTAGG,iTru5_03_F,CCTAGAGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F7
1,blank_30_F8,blank_30_F8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K15,iTru7_106_05,CACAAGTC,iTru5_04_F,TTCCAGGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F8
1,blank_30_F9,blank_30_F9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},K17,iTru7_106_06,TCTTGACG,iTru5_05_F,TCAGCCTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.F9
1,blank_30_G1,blank_30_G1,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M1,iTru7_106_10,GTACCTTG,iTru5_09_F,AACACTGG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G1
1,blank_30_G10,blank_30_G10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M19,iTru7_107_07,CCGACTAT,iTru5_06_G,GATCTTGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G10
1,blank_30_G11,blank_30_G11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M21,iTru7_107_08,AGCTAACC,iTru5_07_G,GTTAAGCG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G11
1,blank_30_G12,blank_30_G12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M23,iTru7_107_09,GCCTTGTT,iTru5_08_G,GTCATCGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G12
1,blank_30_G2,blank_30_G2,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M3,iTru7_106_11,GACTATGC,iTru5_10_F,ACTATCGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G2
1,blank_30_G3,blank_30_G3,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M5,iTru7_106_12,TGGATCAC,iTru5_11_F,ACAACAGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G3
1,blank_30_G4,blank_30_G4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M7,iTru7_107_01,CTCTGGTT,iTru5_12_F,TGTGGCTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G4
1,blank_30_G5,blank_30_G5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M9,iTru7_107_02,GTTCATGG,iTru5_01_G,GTTCCATG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G5
1,blank_30_G6,blank_30_G6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M11,iTru7_107_03,GCTGTAAG,iTru5_02_G,TGGATGGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G6
1,blank_30_G7,blank_30_G7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M13,iTru7_107_04,GTCGAAGA,iTru5_03_G,GCATAACG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G7
1,blank_30_G8,blank_30_G8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M15,iTru7_107_05,GAGCTCAA,iTru5_04_G,TCGAACCT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G8
1,blank_30_G9,blank_30_G9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},M17,iTru7_107_06,TGAACCTG,iTru5_05_G,ACATGCCA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.G9
1,blank_30_H1,blank_30_H1,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O1,iTru7_107_10,AACTTGCC,iTru5_09_G,TCAGACAC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H1
1,blank_30_H10,blank_30_H10,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O19,iTru7_108_07,GAAGTACC,iTru5_06_H,CCTCGTTA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H10
1,blank_30_H11,blank_30_H11,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O21,iTru7_108_08,CAGGTATC,iTru5_07_H,CGATTGGA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H11
1,blank_30_H12,blank_30_H12,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O23,iTru7_108_09,TCTCTAGG,iTru5_08_H,CCAACGAA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H12
1,blank_30_H2,blank_30_H2,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O3,iTru7_107_11,CAATGTGG,iTru5_10_G,GTCCTAAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H2
1,blank_30_H3,blank_30_H3,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O5,iTru7_107_12,AAGGCTGA,iTru5_11_G,AGACCTTG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H3
1,blank_30_H4,blank_30_H4,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O7,iTru7_108_01,TTACCGAG,iTru5_12_G,AGACATGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H4
1,blank_30_H5,blank_30_H5,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O9,iTru7_108_02,GTCCTAAG,iTru5_01_H,TAGCTGAG,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H5
1,blank_30_H6,blank_30_H6,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O11,iTru7_108_03,GAAGGTTC,iTru5_02_H,TTCGAAGC,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H6
1,blank_30_H7,blank_30_H7,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O13,iTru7_108_04,GAAGAGGT,iTru5_03_H,CAGTGCTT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H7
1,blank_30_H8,blank_30_H8,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O15,iTru7_108_05,TCTGAGAG,iTru5_04_H,TAGTGCCA,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H8
1,blank_30_H9,blank_30_H9,Test Shotgun Library \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},O17,iTru7_108_06,ACCGCATA,iTru5_05_H,GATGGAGT,New sequencing run \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6},blank.30.H9"""  # noqa


if __name__ == '__main__':
    integration_tests()
