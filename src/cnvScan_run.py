#!/usr/bin/env python

import sys, os
import pybedtools
import pysam
import vcf
import re
import vcf
import numpy as np
from scipy.stats import mannwhitneyu
import filt_cnvs
import annotate
import argparse


class cnv_scan(object):

    def __init__(self, input, output, resources, database):
        self.input = input
        self.output = output
        self.resources = resources
        self.db = database

        self.annotate()
        self.dump()

    def annotate(self):

        db_file = pysam.TabixFile(self.db)

        cnv_anno = {}
        cnv_anno, cnvs_ordered = filt_cnvs.read_cnvRes(self.input, cnv_anno)
        cnv_anno = filt_cnvs.db_search(db_file, cnv_anno) # cnv_anno = filt_cnvs.db_search(db_file, db_id, cnv_anno) #

        a_cnv = annotate.create_bedTools(self.input)
        b_gencode = pybedtools.BedTool(os.path.join(self.resources, "havana_or_ensembl_gencode.v19.annotation.gtf"))
        c_conradCNV = pybedtools.BedTool(os.path.join(self.resources, "conrad.et.al.2010_Validated_CNVEs_v5_4Release.tab"))
        d_dgvCNV = pybedtools.BedTool(os.path.join(self.resources, "dgv_GRCh37_hg19_variants_2014-10-16.tab"))
        d_dgvFiltsCNV_l2 = pysam.TabixFile(os.path.join(self.resources, "cnvMap_stringencyLevel2.bed.gz"))
        d_dgvFiltsCNV_l12 = pysam.TabixFile(os.path.join(self.resources, "cnvMap_stringencyLevel12.bed.gz"))
        e_phastCon = pysam.TabixFile(os.path.join(self.resources, "phastConsElements100wayFormatted.bed.gz"))
        f_haploIdx = pysam.TabixFile(os.path.join(self.resources, "haploinsufficiencyindex_withimputation.bed.gz"))
        g_del1000g_delFile = pysam.TabixFile(os.path.join(self.resources, "union.2010_06.deletions.sites.vcf.gz"))
        h_dup1000g_delFile = pysam.TabixFile(os.path.join(self.resources, "union.2010_09.TandemDuplications.genotypes.vcf.gz"))
        i_clinVar_reader = vcf.Reader(open(os.path.join(self.resources, "clinvar_20150106.vcf.gz"), 'r'))
        j_omim_file = os.path.join(self.resources, "morbidmap_formatted_onlyHGNC.txt")
        h_devDis_file = os.path.join(self.resources, "cnvScan_DDG2P_freeze_with_gencode19_genomic_coordinates_20141118.txt")
        i_genIntol_file = os.path.join(self.resources, "GeneticIntollarenceScore_RVIS_OERatioPercentile.txt")

        cnv_anno = annotate.gencode_annotate(a_cnv, b_gencode, cnv_anno)
        cnv_anno = annotate.sanger_annotate(a_cnv, c_conradCNV, cnv_anno)
        cnv_anno = annotate.dgv_annotate(a_cnv, d_dgvCNV, cnv_anno)
        cnv_anno = annotate.dgvFilt_annotate(d_dgvFiltsCNV_l2, cnv_anno, "DGV_Stringency2")
        cnv_anno = annotate.dgvFilt_annotate(d_dgvFiltsCNV_l12, cnv_anno, "DGV_Stringency12")
        cnv_anno = annotate.phastCon_annotate(e_phastCon, cnv_anno)
        cnv_anno = annotate.haploIdx_annotate(f_haploIdx, cnv_anno)
        cnv_anno = annotate.geneticIntolarance_annotate(i_genIntol_file, cnv_anno)
        cnv_anno = annotate.del1000g_annotate(g_del1000g_delFile, cnv_anno)
        cnv_anno = annotate.dup1000g_annotate(h_dup1000g_delFile, cnv_anno)
        cnv_anno = annotate.clinVar_annotate(i_clinVar_reader, cnv_anno)
        cnv_anno = annotate.omim_annotate(j_omim_file, cnv_anno)
        cnv_anno = annotate.devDisorder_annotate(h_devDis_file, cnv_anno)

        self.cnv_anno = cnv_anno
        self.cnvs_ordered = cnvs_ordered


    def dump(self):
        header_line= ["chr", "start", "end", "cnv_state", "default_score","len"]
        header_line.extend(["inDB_count", "inDBScore_MinMaxMedian"])
        header_line.extend(["gene_name", "gene_type", "gene_id", "exon_count", "UTR", "transcript"])
        header_line.extend(["phastConElement_count", "phastConElement_minMax"])
        header_line.extend(["haplo_insufIdx_count", "haplo_insufIdx_score"])
        header_line.append("Gene_intolarance_score")
        header_line.append("sanger_cnv")
        header_line.extend(["dgv_cnv", "dgv_varType", "dgv_varSubType", "dgv_pubmedId", 'DGV_Stringency2_count', 'DGV_Stringency2_PopFreq', 'DGV_Stringency12_count', 'DGV_Stringency12_popFreq'])
        header_line.extend(["1000g_del","1000g_ins"])
        header_line.append("omim_morbidMap")
        header_line.extend(["ddd_mutConsequence", "ddd_diseaseName", "ddd_pubmedId"])
        header_line.extend(["clinVar_disease", "hgvs_varName"])

        out_file = open(self.output, 'w')

        out_file.write("\t".join(header_line)+"\n")

        for k in self.cnvs_ordered:
            line = k.split(":")
            line.extend([str(self.cnv_anno[k]['CNV_st']), self.cnv_anno[k]['score'], str(int(line[2])-int(line[1])) ])
            line.extend([ str(self.cnv_anno[k]['inDB_count']), str(self.cnv_anno[k]['inDB_minmaxmedian']) ])
            lst_name = []
            exon_c = []

            if self.cnv_anno[k].get('gene_name'):
                for k1 in self.cnv_anno[k]['gene_name']: lst_name.append( ":".join( [k1, self.cnv_anno[k]['gene_name'][k1]] ))
                line.append("|".join(lst_name))
                line.append(";".join(self.cnv_anno[k]['gene_type'].keys()))
                line.append(";".join(self.cnv_anno[k]['gene_id'].keys()))
                if self.cnv_anno[k].get("exon_count"):
                    for k1 in self.cnv_anno[k]['exon_count']: exon_c.append( ":".join( [k1, str(self.cnv_anno[k]['exon_count'][k1])] ))
                    line.append("|".join(exon_c))
                else:
                    line.append("NA")
                if self.cnv_anno[k].get('UTR'):
                    line.append(self.cnv_anno[k]['UTR'])
                else:
                    line.append("NA")
            else:
                self.cnv_anno[k]['gene_name'] = "NA"
                line.append(self.cnv_anno[k]['gene_name'])
                self.cnv_anno[k]['gene_type'] = "NA"
                line.append(self.cnv_anno[k]['gene_type'])
                self.cnv_anno[k]['gene_id'] = "NA"
                line.append(self.cnv_anno[k]['gene_id'])
                self.cnv_anno[k]['exon_count'] = "NA"
                line.append(self.cnv_anno[k]['exon_count'])
                self.cnv_anno[k]['UTR'] = "NA"
                line.append(self.cnv_anno[k]['UTR'])
            if self.cnv_anno[k].get('transcript'):
                line.append(self.cnv_anno[k]['transcript'])
            else:
                self.cnv_anno[k]['transcript'] = "NA"
                line.append(self.cnv_anno[k]['transcript'])
            line.append(str(self.cnv_anno[k]['phastCon_count']))
            line.append(str(self.cnv_anno[k]['phastCon_min_max']))
            line.append(str(self.cnv_anno[k]['haploIdx_count']))
            line.append(str(self.cnv_anno[k]['haploIdx_score']))
            line.append(str(self.cnv_anno[k]['GenInTolScore'])) #
            if self.cnv_anno[k].get('Sanger_HiRes_CNV'):
                line.append(str(self.cnv_anno[k]['Sanger_HiRes_CNV']))
            else:
                self.cnv_anno[k]['Sanger_HiRes_CNV'] = "NA"
                line.append(self.cnv_anno[k]['Sanger_HiRes_CNV'])
            if self.cnv_anno[k].get('DGV_CNV'):
                line.append(str(self.cnv_anno[k]['DGV_CNV']))
                line.append(str(self.cnv_anno[k]['DGV_VarType']))
                line.append(str(self.cnv_anno[k]['DGV_VarSubType']))
                line.append(str(self.cnv_anno[k]['DGV_PUBMEDID']))
            else:
                self.cnv_anno[k]['DGV_CNV'] = "NA"
                self.cnv_anno[k]['DGV_VarType'] = "NA"
                self.cnv_anno[k]['DGV_VarSubType'] = "NA"
                self.cnv_anno[k]['DGV_PUBMEDID'] = "NA"
                line.append(self.cnv_anno[k]['DGV_CNV'])
                line.append(self.cnv_anno[k]['DGV_VarType'])
                line.append(self.cnv_anno[k]['DGV_VarSubType'])
                line.append(self.cnv_anno[k]['DGV_PUBMEDID'])
            if self.cnv_anno[k].get('DGV_Stringency2_count'):
                line.append(str(self.cnv_anno[k]['DGV_Stringency2_count']))   #
                line.append(str(self.cnv_anno[k]['DGV_Stringency2_popFreq'])) #
            else:
                self.cnv_anno[k]['DGV_Stringency2_count'] = "NA"
                self.cnv_anno[k]['DGV_Stringency2_popFreq'] = "NA"
                line.append(str(self.cnv_anno[k]['DGV_Stringency2_count']))
                line.append(str(self.cnv_anno[k]['DGV_Stringency2_popFreq']))
            if self.cnv_anno[k].get('DGV_Stringency12_count'):
                line.append(str(self.cnv_anno[k]['DGV_Stringency12_count']))   #
                line.append(str(self.cnv_anno[k]['DGV_Stringency12_popFreq'])) #
            else:
                self.cnv_anno[k]['DGV_Stringency12_count'] = "NA"
                self.cnv_anno[k]['DGV_Stringency12_popFreq'] = "NA"
                line.append(str(self.cnv_anno[k]['DGV_Stringency12_count']))
                line.append(str(self.cnv_anno[k]['DGV_Stringency12_popFreq']))
            line.append(str(self.cnv_anno[k]['1000G_Del_count']))
            line.append(str(self.cnv_anno[k]['1000G_Dup_count']))
            line.append(self.cnv_anno[k]['OMIM'])
            line.append(self.cnv_anno[k]['devDis_mutConseq'])
            line.append(self.cnv_anno[k]['devDis_disName'])
            line.append(self.cnv_anno[k]['devDis_pubmedID'])
            line.append(str(self.cnv_anno[k]['clindbn']))
            line.append(str(self.cnv_anno[k]['clinhgvs']))
            out_file.write("\t".join(line) + "\n")
            #print "\t".join(line), len(line)


# ============================================================
def main():
        '''
        cnvScan
        '''
        parser = argparse.ArgumentParser(
            description='Annotate CNV prediction with resource data')
        parser.add_argument('-i', '--input', type=str, required=True,
                            help='Input bed file')
        parser.add_argument('-o', '--output', type=str, required=True,
                            help='Output bed file')
        parser.add_argument('-s', '--resources', type=str, required=True,
                            help='Path to resource folder')
        parser.add_argument('-db', '--database', type=str, required=True,
                            help='In-house database file')
        args = parser.parse_args()

        neighbor = cnv_scan(args.input, args.output, args.resources, args.database)


# ============================================================
if __name__ == "__main__":
    sys.exit(main())
