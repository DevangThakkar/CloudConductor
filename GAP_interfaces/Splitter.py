import logging
import os
from GAP_interfaces import Module

class Splitter(Module):

    def __init__(self, platform, tool_id, main_module_name=None):
        super(Splitter, self).__init__(platform, tool_id)

        self.input_keys  = None
        self.output_keys = None

        # Optionally set name of splitter module to the name of the main tool using the splitter
        # Conceptually links splitter/tool/merger when being used as if they were a single module
        self.main_module_name = main_module_name if main_module_name is not None else self.__class__.__name__

    def check_init(self):
        cls_name = self.__class__.__name__

        # Generate the set of keys that are required for a class instance
        required_keys = {
            "input_keys":   self.input_keys,
            "output_keys":  self.output_keys,

            "req_tools":       self.req_tools,
            "req_resources":   self.req_resources,
        }

        # Check if class instance has initialized all the attributes
        for (key_name, attribute) in required_keys.iteritems():
            if attribute is None:
                raise NotImplementedError(
                    "In module %s, the attribute \"%s\" was not initialized!" % (cls_name, key_name))

    def check_input(self, provided_keys):
        return [ key for key in self.input_keys if key not in provided_keys ]

    def define_output(self):
        return self.output_keys

    def get_nr_splits(self):
        return len(self.get_output())

    def generate_command(self, **kwargs):

        #initialize list for holding split info, names of output files
        self.output = list()

        # Get information about each split
        self.init_split_info(**kwargs)

        # Set output file names
        self.init_output_file_paths(**kwargs)

        # Check output file names
        self.check_output_files()

        # Get command for splitting input file and generating split output files
        cmd = self.get_command(**kwargs)

        return cmd

    def init_split_info(self, **kwargs):
        raise NotImplementedError("In module %s, the function \"get_split_info\" was not implemented" % self.__class__.__name__)

    def init_output_file_paths(self, **kwargs):
        raise NotImplementedError("In module %s, the function \"init_output_file_paths\" was not implemented" % self.__class__.__name__)

    def generate_output_file_path(self, output_key, **kwargs):
        # Generate the name of an output file for a module
        # Called inside 'get_command' function of module to get standardized names of output files
        # Automatically adds output key pair to module's dict of output files generated (i.e. self.output)
        # Throws error if generated filename collides with existing input/output filenames


        output_file_path = kwargs.get("output_file_path", None)
        split_id = kwargs.get("split_id", None)

        # Check to make sure a split_id has been provided
        if split_id is None:
            logging.error(
                "Failed to provide split index to generate_output_file_path function in module: %s." % self.__class__.__name__)
            raise NotImplementedError(
                "Failed to provide split index to generate_output_file_path function in module: %s." % self.__class__.__name__)

        # If file_path is not specified in kwargs, automatically generate output filename
        # Otherwise, add the name of the output file specified directly to self.output
        if output_file_path is None:
            output_dir  = kwargs.get("output_dir",  self.tmp_dir)
            split_name  = kwargs.get("split_name",  None)
            extension   = kwargs.get("extension",   None)
            prefix      = self.pipeline_data.get_pipeline_name()


            # Get name of split
            split_string = ".splitter.split.%s" % (str(split_name)) if split_name is not None else ".splitter.split.%s" % (str(split_id))

            # Standardize formatting of extensions (set extension to nothing if no extension specified
            extension = ".%s" % str(extension).lstrip(".")

            # Generate standardized filename
            output_file_name = "%s_%s_%s%s%s" % (prefix,
                                                 self.main_module_name,
                                                 self.tool_id,
                                                 split_string,
                                                 extension)

            # Add pathname to filename
            output_file_path = os.path.join(output_dir, output_file_name)

        # Check to make sure output file path doesn't collide with existing filenames in the module
        self.check_for_path_collisions(output_key, output_file_path, split_id=split_id)

        # Add output file to self.output
        self.output[split_id][output_key] = output_file_path

        return output_file_path

    def check_output_files(self):
        errors = False
        for required_key in self.output_keys:
            for split_output in self.output:
                if required_key not in split_output:
                    logging.error("Runtime error: Required output file type '%s' is never generated by splitter module '%s' during runtime." % (required_key, self.__class__.__name__))
                    errors = True
        if errors:
            raise NotImplementedError("One or more required output file types are never generated by the get_command function of splitter module: '%s'. Please see the errors above for details."
                                      % self.__class__.__name__)

    def check_for_path_collisions(self, check_key, check_file, **kwargs):

        # Get split id of original split output file
        check_split_id = kwargs.get("split_id", None)

        # Checks to see if a filename collides with an existing filename either in the current set of output files
        for split_id in range(len(self.output)):
            if split_id != check_split_id:
                split = self.output[split_id]
                if check_key in split:
                    if split[check_key] == check_file:
                        logging.error("Attempted to create two or more output files with the same name in the same module: %s. Please modify names of output files in module '%s'."
                                % (check_file, self.__class__.__name__))
                        raise IOError("Attempted to create two or more output files with the same name in module '%s'. See above for details!" %
                                self.__class__.__name__)




