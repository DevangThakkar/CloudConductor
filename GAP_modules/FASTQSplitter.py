from GAP_interfaces import Main
import os

class FASTQSplitter(Main):

    def __init__(self, config):
        Main.__init__(self, config)

        self.temp_dir = config.general.temp_dir

    def byNrReads(self, file_path, type, nr_reads):

        # Setting the required values in the object
        self.file_path  = file_path
        self.type       = type
        self.nr_reads   = nr_reads

        # Validating the values
        self.validate()

        self.message("Splitting FASTQ file by %d reads." % self.nr_reads)

        # Splitting the file
        split_count = 0
        with open(self.file_path) as f:
            
            done = False
          
            while not done:
    
                # Creating a new split file, considering the original fastq type
                split_count    += 1
                
                if self.type == "PE_R1":
                    split_filename  = "split_R1_%d.fastq" % split_count
                elif self.type == "PE_R2":
                    split_filename  = "split_R2_%d.fastq" % split_count
                elif self.type == "SE":
                    split_filename  = "split_%d.fastq" % split_count
                else:
                    self.warning("Unrecognized FASTQ file type '%s' in the pipeline. Default: Single-End.") 
                    split_filename  = "split_%d.fastq" % split_count

                split_filepath  = "%s/%s" % (self.temp_dir, split_filename)

                self.message("Writing to split file %s." % split_filename)

                # Writing to the new split file
                with open(split_filepath, "w") as out:

                    # Copying maximum nr_reads*4 lines
                    for i in range(nr_reads*4):
                        line = f.readline()
            
                        if line != "":
                            out.write(line)
                        else:
                            done = True
                            break

                # Deleting split if empty (possible when total_reads % nr_reads == 0)
                if os.path.getsize(split_filepath) == 0:
                    os.remove(split_filepath)
                    split_count -= 1

        self.message("Splitting FASTQ file has been completed.")

        return split_count

    def validate(self):
        
        if not os.path.isfile(self.file_path):
            self.error("Input file could not be found!")

        if self.nr_reads <= 0:
            self.error("Cannot split a FASTQ file by %d reads!" % self.nr_reads)
