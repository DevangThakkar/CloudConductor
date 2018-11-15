from Modules import Merger, PseudoMerger
from System.Platform import Platform

class _GATKBase(Merger):

    def __init__(self, module_id, is_docker=False):
        super(_GATKBase, self).__init__(module_id, is_docker)

    def define_base_args(self):

        # Set GATK executable arguments
        self.add_argument("java",           is_required=True, is_resource=True)
        self.add_argument("gatk",           is_required=True, is_resource=True)
        self.add_argument("gatk_version",   is_required=True)

        # Set reference specific arguments
        self.add_argument("ref",            is_required=True, is_resource=True)
        self.add_argument("ref_idx",        is_required=True, is_resource=True)
        self.add_argument("ref_dict",       is_required=True, is_resource=True)

        # Set chromosome interval specific arguments
        self.add_argument("location")
        self.add_argument("excluded_location")

    def get_gatk_command(self):
        # Get input arguments
        gatk        = self.get_argument("gatk")
        mem         = self.get_argument("mem")
        java        = self.get_argument("java")
        jvm_options = "-Xmx{0}G -Djava.io.tmpdir={1}".format(mem * 4/5, "/tmp/")

        # Determine numeric version of GATK
        gatk_version = self.get_argument("gatk_version")
        gatk_version = str(gatk_version).lower().replace("gatk","")
        gatk_version = gatk_version.strip()
        gatk_version = int(gatk_version.split(".")[0])

        if gatk_version < 4:
            return "{0} {1} -jar {2} -T".format(java, jvm_options, gatk)

        # Generate base command with endpoint provided by docker
        else:
            return "{0} {1} -jar {2}".format(java, jvm_options, gatk)

    @staticmethod
    def get_output_file_flag():
        """
        Function returns an appropriate output file flag for GATK tools based on GATK version
        Returns: Output file flag in Str format

        """

        # Determine numeric version of GATK
        gatk_version = self.get_argument("gatk_version")
        gatk_version = str(gatk_version).lower().replace("gatk", "")
        gatk_version = gatk_version.strip()
        gatk_version = int(gatk_version.split(".")[0])

        if gatk_version < 4:
            return "-o"

        return "-O"

class GenotypeGVCFs(_GATKBase):

    def __init__(self, module_id, is_docker=False):
        super(GenotypeGVCFs, self).__init__(module_id, is_docker)
        self.output_keys = ["vcf", "vcf_idx"]

    def define_input(self):
        self.define_base_args()
        self.add_argument("gvcf",                is_required=True)
        self.add_argument("gvcf_idx",            is_required=True)
        self.add_argument("nr_cpus",            is_required=True, default_value=6)
        self.add_argument("mem",                is_required=True, default_value=35)

    def define_output(self):
        # Declare VCF output filename
        vcf = self.generate_unique_file_name(extension=".vcf")
        self.add_output("vcf", vcf)
        # Declare VCF index output filename
        vcf_idx = self.generate_unique_file_name(extension=".vcf.idx")
        self.add_output("vcf_idx", vcf_idx)

    def define_command(self):
        # Get input arguments
        gvcf_in     = self.get_argument("gvcf")
        ref         = self.get_argument("ref")
        L           = self.get_argument("location")
        XL          = self.get_argument("excluded_location")
        vcf         = self.get_output("vcf")
        gatk_cmd    = self.get_gatk_command()

        output_file_flag = self.get_output_file_flag()

        # Generating the haplotype caller options
        opts = list()

        if isinstance(gvcf_in, list):
            for gvcf in gvcf_in:
                opts.append("--variant %s" % gvcf)
        else:
            opts.append("--variant %s" % gvcf_in)
        opts.append("{0} {1}".format(output_file_flag, vcf))
        opts.append("-R %s" % ref)

        # Limit the locations to be processes
        if L is not None:
            if isinstance(L, list):
                for included in L:
                    if included != "unmapped":
                        opts.append("-L \"%s\"" % included)
            else:
                opts.append("-L \"%s\"" % L)
        if XL is not None:
            if isinstance(XL, list):
                for excluded in XL:
                    opts.append("-XL \"%s\"" % excluded)
            else:
                opts.append("-XL \"%s\"" % XL)

        # Generating command for base recalibration
        return "touch {0}/*.idx; {1} GenotypeGVCFs {2} !LOG3!".format(self.get_output_dir(), gatk_cmd, " ".join(opts))

class Mutect2(_GATKBase):

    def __init__(self, module_id, is_docker=False):
        super(Mutect2, self).__init__(module_id, is_docker)
        self.output_keys = ["vcf", "vcf_idx"]

    def define_input(self):
        self.define_base_args()
        self.add_argument("bam",                is_required=True)
        self.add_argument("bam_idx",            is_required=True)
        self.add_argument("sample_name",        is_required=True)
        self.add_argument("is_tumor",           is_required=True)
        self.add_argument("germline_vcf",       is_required=False,  is_resource=True)
        self.add_argument("nr_cpus",            is_required=True,   default_value=8)
        self.add_argument("mem",                is_required=True,   default_value=30)

    def define_output(self):
        # Declare VCF output filename
        vcf = self.generate_unique_file_name(extension=".vcf")
        self.add_output("vcf", vcf)
        # Declare VCF index output filename
        vcf_idx = self.generate_unique_file_name(extension=".vcf.idx")
        self.add_output("vcf_idx", vcf_idx)

    def define_command(self):
        # Get input arguments
        bams            = self.get_argument("bam")
        sample_names    = self.get_argument("sample_name")
        is_tumor        = self.get_argument("is_tumor")
        ref             = self.get_argument("ref")
        germline_vcf    = self.get_argument("germline_vcf")
        L               = self.get_argument("location")
        XL              = self.get_argument("excluded_location")
        nr_cpus         = self.get_argument("nr_cpus")
        vcf             = self.get_output("vcf")

        gatk_cmd        = self.get_gatk_command()

        output_file_flag = self.get_output_file_flag()

        # Generating the MuTect2 options
        opts = list()

        # Add Tumor/Normal sample names
        if is_tumor[0]:
            opts.append("-tumor %s" % sample_names[0])
            opts.append("-normal %s" % sample_names[1])
        else:
            opts.append("-tumor %s" % sample_names[1])
            opts.append("-normal %s" % sample_names[0])

        # Add arguments for bams
        tumor_bams = ["-I %s" % bam for bam in bams[0] ] if isinstance(bams[0], list) else ["-I %s" % bams[0]]
        normal_bams = ["-I %s" % bam for bam in bams[1] ] if isinstance(bams[1], list) else ["-I %s" % bams[1]]
        opts += tumor_bams + normal_bams

        opts.append("{0} {1}".format(output_file_flag, vcf))
        opts.append("-R %s" % ref)
        opts.append("--native-pair-hmm-threads %s" % nr_cpus)

        if germline_vcf is not None:
            opts.append("--germline-resource %s" % germline_vcf)

        # Limit the locations to be processes
        if L is not None:
            if isinstance(L, list):
                for included in L:
                    if included != "unmapped":
                        opts.append("-L \"%s\"" % included)
            else:
                opts.append("-L \"%s\"" % L)
        if XL is not None:
            if isinstance(XL, list):
                for excluded in XL:
                    opts.append("-XL \"%s\"" % excluded)
            else:
                opts.append("-XL \"%s\"" % XL)

        # Generating command for Mutect2
        return "{0} Mutect2 {1} !LOG3!".format(gatk_cmd, " ".join(opts))

class MergeBQSRs(_GATKBase):

    def __init__(self, module_id, is_docker=False):
        super(MergeBQSRs, self).__init__(module_id, is_docker)
        self.output_keys  = ["BQSR_report"]

    def define_input(self):
        self.define_base_args()
        self.add_argument("BQSR_report",    is_required=True)
        self.add_argument("nr_cpus",        is_required=True, default_value=8)
        self.add_argument("mem",            is_required=True, default_value="nr_cpus * 2")

    def define_output(self):
        # Declare merged bam output file
        bqsr_out = self.generate_unique_file_name(extension=".merged.grp")
        self.add_output("BQSR_report", bqsr_out)

    def define_command(self):
        # Obtaining the arguments
        bqsrs_in    = self.get_argument("BQSR_report")
        bqsr_out    = self.get_output("BQSR_report")
        gatk_cmd    = self.get_gatk_command()

        output_file_flag = self.get_output_file_flag()

        return "{0} GatherBQSRReports --input {1} {3} {2} !LOG3!".format(gatk_cmd, " --input ".join(bqsrs_in),
                                                                         bqsr_out, output_file_flag)

class CatVariants(_GATKBase):
    # Merger module intended to merge gVCF files within samples (i.e. re-combine chromosomes)

    def __init__(self, module_id, is_docker=False):
        super(CatVariants, self).__init__(module_id, is_docker)
        self.output_keys  = ["gvcf", "gvcf_idx"]

    def define_input(self):
        self.define_base_args()
        self.add_argument("gvcf",       is_required=True)
        self.add_argument("gvcf_idx",   is_required=True)
        self.add_argument("nr_cpus",    is_required=True, default_value=2)
        self.add_argument("mem",        is_required=True, default_value=13)

    def define_output(self):
        # Declare GVCF output filename
        randomer = Platform.generate_unique_id()
        gvcf = self.generate_unique_file_name(extension="{0}.g.vcf".format(randomer))
        self.add_output("gvcf", gvcf)
        # Declare GVCF index output filename
        gvcf_idx = self.generate_unique_file_name(extension="{0}.g.vcf.idx".format(randomer))
        self.add_output("gvcf_idx", gvcf_idx)

    def define_command(self):
        # Obtaining the arguments
        gvcf_in     = self.get_argument("gvcf")
        gatk        = self.get_argument("gatk")
        java        = self.get_argument("java")
        ref         = self.get_argument("ref")
        mem         = self.get_argument("mem")
        gvcf_out    = self.get_output("gvcf")

        # Generating JVM options
        jvm_options = "-Xmx%dG -Djava.io.tmpdir=/tmp/" % (mem * 9 / 10)

        output_file_flag = self.get_output_file_flag()

        # Generating the CatVariants options
        opts = list()
        opts.append("{0} {1}".format(output_file_flag, gvcf_out))
        opts.append("-R %s" % ref)
        if isinstance(gvcf_in, list):
            for gvcf_input in gvcf_in:
                opts.append("-V %s" % gvcf_input)
        else:
            opts.append("-V %s" % gvcf_in)

        # Generating the combine command
        cmd = "%s %s -cp %s org.broadinstitute.gatk.tools.CatVariants %s !LOG3!" % (java,
                                                                                    jvm_options,
                                                                                    gatk,
                                                                                    " ".join(opts))
        return cmd

class CombineGVCF(_GATKBase):
    # Merger module intended to merge gVCF files across multiple samples
    def __init__(self, module_id, is_docker=False):
        super(CombineGVCF, self).__init__(module_id, is_docker)
        self.output_keys  = ["gvcf", "gvcf_idx"]

    def define_input(self):
        self.define_base_args()
        self.add_argument("gvcf",               is_required=True)
        self.add_argument("gvcf_idx",           is_required=True)
        self.add_argument("nr_cpus",            is_required=True, default_value=8)
        self.add_argument("mem",                is_required=True, default_value=16)

    def define_output(self):
        # Declare GVCF output filename
        randomer = Platform.generate_unique_id()
        gvcf = self.generate_unique_file_name(extension="{0}.g.vcf".format(randomer))
        self.add_output("gvcf", gvcf)
        # Declare GVCF index output filename
        gvcf_idx = self.generate_unique_file_name(extension="{0}.g.vcf.idx".format(randomer))
        self.add_output("gvcf_idx", gvcf_idx)

    def define_command(self):

        # Obtaining the arguments
        gvcf_list   = self.get_argument("gvcf")
        ref         = self.get_argument("ref")
        L           = self.get_argument("location")
        XL          = self.get_argument("excluded_location")
        gvcf_out    = self.get_output("gvcf")

        gatk_cmd    = self.get_gatk_command()

        output_file_flag = self.get_output_file_flag()

        # Generating the combine options
        opts = list()
        opts.append("{0} {1}".format(output_file_flag, gvcf_out))
        opts.append("-R %s" % ref)
        opts.append("-U ALLOW_SEQ_DICT_INCOMPATIBILITY") # Option that allows dictionary incompatibility
        for gvcf_input in gvcf_list:
            opts.append("-V %s" % gvcf_input)

        # Limit the locations to be processes
        if L is not None:
            if isinstance(L, list):
                for included in L:
                    if included != "unmapped":
                        opts.append("-L \"%s\"" % included)
            else:
                opts.append("-L \"%s\"" % L)
        if XL is not None:
            if isinstance(XL, list):
                for excluded in XL:
                    opts.append("-XL \"%s\"" % excluded)
            else:
                opts.append("-XL \"%s\"" % XL)

        # Generating the combine command
        return "{0} CombineGVCFs {1} !LOG3!".format(gatk_cmd, " ".join(opts))

class GenomicsDBImport(PseudoMerger):
    # Merger module intended to merge gVCF files across multiple samples
    def __init__(self, module_id, is_docker=False):
        super(GenomicsDBImport, self).__init__(module_id, is_docker)
        self.output_keys  = ["genomicsDB"]

    def define_input(self):
        self.add_argument("java",           is_required=True, is_resource=True)
        self.add_argument("gatk",           is_required=True, is_resource=True)
        self.add_argument("gvcf",           is_required=True)
        self.add_argument("gvcf_idx",       is_required=True)
        self.add_argument("batch_size",     is_required=True,   default_value=50)
        self.add_argument("interval_pad",   is_required=False,  default_value=None)
        self.add_argument("nr_cpus",        is_required=True,   default_value=5)
        self.add_argument("mem",            is_required=True,   default_value=15)
        self.add_argument("location")
        self.add_argument("excluded_location")

    def define_output(self):
        # Declare merged GVCF output filename
        genomicsDB = self.generate_unique_file_name(extension="genomicsDB")
        self.add_output("genomicsDB", genomicsDB)

    def define_command(self):

        # Obtaining the arguments
        gatk            = self.get_argument("gatk")
        mem             = self.get_argument("mem")
        java            = self.get_argument("java")
        gvcf_list       = self.get_argument("gvcf")
        nr_cpus         = self.get_argument("nr_cpus")
        batch_size      = self.get_argument("batch_size")
        interval_pad    = self.get_argument("interval_pad")
        L               = self.get_argument("location")
        genomicsDB      = self.get_output("genomicsDB")

        # Make JVM options and GATK command
        jvm_options = "-Xmx{0}G -Xms{0}G -Djava.io.tmpdir={1}".format(mem * 3 / 5, "/tmp/")
        gatk_cmd    = "{0} {1} -jar {2}".format(java, jvm_options, gatk)

        # Generating the combine options
        opts = list()

        # Add input gvcfs
        for gvcf_input in gvcf_list:
            opts.append("-V {0}".format(gvcf_input))

        # Add threads option
        opts.append("--reader-threads {0}".format(nr_cpus))
        opts.append("--batch-size {0}".format(batch_size))
        opts.append("--genomicsdb-workspace-path {0}".format(genomicsDB))

        # Add interval pad if necessary
        if interval_pad is not None:
            opts.append("-ip {0}".format(interval_pad))

        # Limit the locations to be processes
        if L is not None:
            if isinstance(L, list):
                for included in L:
                        opts.append("-L \"%s\"" % included)
            else:
                opts.append("-L \"%s\"" % L)

        # Generate command to make genomicsDB directory and run job
        return "rm -rf {0} ; {1} GenomicsDBImport {2} !LOG3!".format(genomicsDB, gatk_cmd, " ".join(opts))