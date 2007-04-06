# Copyright 2007 Pieter Edelman (p _dot_ edelman _at_ gmx _dot_ net)
#
# This file is part of The Big Picture.
# 
# The Big Picture is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# The Big Picture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with The Big Picture; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# 

import byteform, datablock, qdb, types
   
class MetaInfoBlock:
  """ The base class for a particuler kind of metainformation structure, like
      Exif or IPTC info. This class provides the methods for searching over the
      different records for a specific tag. This class functions as a base
      class.
      Each derived class should have a QDB called records, with the following
      lists:
      - num:    the number of each record
      - name:   the name of each record
      - record: an instance of a MetaInfoRecord-derived class
      Furthermore, it should have a dict called DATA_TYPES, where the keys
      are the number of each data type, and the values a class to manipulate
      that particular kind of data.
  """
      
  def getTag(self, tag, record = None, data_type = None):
    """ Return the tag data with the specified number from the specified record.
    """
    
    # Get the record and tag numbers
    try:
      record_num, tag_num = self.__getRecordAndTagNum__(tag, record)
    except KeyError:
      # We're dealing with an unknown tag, but it may have been loaded from disk
      if (type(tag) == types.IntType):
        tag_num = tag
        record_num = self.__getRecordNum__(record)
      if (tag_num == None) and (record_num == None):
        raise TypeError, "Unknown tag %s, please specify tag number and record number" % str(tag)
        
    # Get the data
    if (record_num):
      # Construct the options list to getTag. This method sometimes accepts the
      # data_type argument, and sometimes does not
      gt_args = [tag_num]
      if (data_type):
        gt_args.append(tag_num)
        
      # Retrieve the data
      data = self.records.query("num", record_num, "record").getTag(*gt_args)
      return data
      
    return None
    
  def setTag(self, tag, payload = None, record = None, check = True, data_type = None, data_count = None, data = None):
    """ Set the specified tag in the specified record to the data, overriding
        all other occurences of that tag. If record num is omitted, the method
        will try to figure out which record is meant. """
        
    # Get the record and tag number
    try:
      rec_num, tag_num = self.__getRecordAndTagNum__(tag, record)
    # If we have an unknown tag, check if the data is in the correct format to 
    # set it
    except KeyError:
      if not (record):
        raise "Unknown tag %s, record needed" % str(tag)
      else:
        rec_num = self.__getRecordNum__(record)

      if (type(tag) in [types.IntType, types.LongType]):
        tag_num = tag
      else:
        raise TypeError, "Unknown tag %s, needs to be specified as a number" % str(tag)

    # Set the data.
    if (rec_num):
      self.records.query("num", rec_num, "record").setTag(tag_num, payload, check, data_type, data_count, data)
  
  def removeTag(self, tag, record = None):
    """ Remove the tag with the specified name or number from the strucrure. """
    # Get the record and tag number
    rec_num, tag_num = self.__getRecordAndTagNum__(tag, record)
    
    # Set the data.
    if (rec_num):
      self.records.query("num", rec_num, "record").removeTag(tag_num)
    
  def hasTags(self):
    """ Returns True of the structure has any tags set, or False otherwise. """
    
    has_tags = False
    for record in self.records.getList("record"):
      has_tags = has_tags or record.hasTags()
      
    return has_tags
    
  def __getRecordNum__(self, record):
    """ Return the record number based on a record number or name. """
    
    # Test numerical input
    if (type(record) == types.IntType):
      if record in self.records.getList("num"):
        return record
      else:
        raise ValueError, "Unknown record %d!" % record
    # Test text input
    elif (type(record) == types.StringType):
      index = self.records.query("name", record)
      if (index):
        return self.records.query(index, "num")
      else:
        raise ValueError, "Unknown record %s!" % record
    else:
      raise TyepError, "I can't make sense of an record of type %s!" % type(record)

  def __getRecordAndTagNum__(self, tag, record = None):
    """ Return the record number and tag number for the supplied tag number or
        name in the specified record name or number. If record is omitted, the
        method will search in all records and raise an error if ambiguousnesses
        are found. """
      
    # If the user didn't specify a record, we search through all records
    if (record == None):
      records = self.records.getList("num")
    # Otherwise, we need to have a record number
    else:
      records = [self.__getRecordNum__(record)]

    # Find the possible records
    found_records = []
    for rec_num in records:
      tag_num = self.records.query("num", rec_num, "record").getTagNum(tag)
      if (tag_num is not False):
        found_records.append([rec_num, tag_num])

    # Warn if the tag occurs in multiple records
    if (len(found_records) == 0):
      raise KeyError, "Tag %s is unknown!" % str(tag)
    elif (len(found_records) > 1):
      raise "Tag %s occurs in multiple records!" % str(tag)
      
    return found_records[0]

class MetaInfoRecord(datablock.DataBlock):
  """ Base class for a metainformation record (like an IFD or an IPTC record). 
      Derived classes should hold create a QDB with the folowing lists:
      - name:      the tag names as strings
      - num:       the tag numbers as integers
      - count:     the number of words in each tag payload as integers or as
                   lists with the minimum and maximum count. None means that
                   this is undefined.
      - data_type: the data type as integer, or as a list of integers.
      They also should have a dict DATA_TYPES, coupling a data type number to
      a data type class.
      Furthermore, each derived class should implement the following methods:
      - getTag(tag_num): return the payload of the tag with the specified
                         number.
      - setTag(tag_num, payload): set the payload of the tag with the specified
                                  number.
      - removeTag(tag_num): remove the tag with the specified number.
  """
  
  def getTagNum(self, tag):
    """ Returns a tag number when fed a tag number or name, or False if it
        doesn't exist within the current record. """
    
    tag_num = False
    
    # Try numeric input
    if (type(tag) == types.IntType):
      if (self.tags.query("num", tag)):
        tag_num = tag
    # Try text input
    elif (type(tag) == types.StringType):
      tag_num = self.tags.query("name", tag, "num")
    else:
      raise TypeError, "Incorrect input type for finding tag numbers."
      
    return tag_num

  def getTagNums(self):
    """ Return a sorted list of set tag nums in this record. """
    
    tag_nums = self.fields.keys()
    tag_nums.sort()
    return tag_nums
    
  def hasTags(self):
    """ Return True if the record has any tags set, or False if not. """
    
    return (len(self.fields) > 0)

class MetaInfoFile:
  """The base class for files containing meta information."""
  
  def __init__(self):
    self.exif = None
    self.IPTC = None
    
  def getExifTag(self, tag, record = None):
    """ Return the payload of the Exif tag with the specified name or number, or
        False if it doesn't exit. The optional record parameter specifies the
        name or number of the record where the tag belongs. """
    
    if (self.exif):
      return self.exif.getTag(tag, record)
    return False
      
  def setExifTag(self, tag, payload = None, record = None, check = True, data_type = None, count = None, data = None):
    """ Set the specified Exif tag name or number. Usually the payload parameter
        specifies the unencoded payload that needs to be set. Alternatively,
        encoded payload may be specified with the data parameter. The optional 
        record parameter specifies the name or number of the record where the
        tag belongs.
        If the tag is unknown, a KeyError is raised. If you still want to set
        the tag, check can be set to False. In this case, a record needs to be 
        specified to store the tag in and a data type for the format.
        Additionaly, if a payload is specified, an optional data count may be
        given for sanity checking.
    """
        
    if (self.exif):
      self.exif.setTag(tag, payload, record, check, data_type, count, data)
  
  def delExifTag(self, tag, record = None):
    """ Remove the Exif tag with the specified name or number. The optional
        record parameter specifies the name or number of the record where the
        tag belongs. """
    if (self.exif):
      self.exif.removeTag(tag, record)
    
  def getIPTCTag(self, tag, record = None, data_type = None):
    """ Return the payload of the IPTC tag or tags with the specified name or
        number, or False if it doesn't exit. The optional record parameter
        specifies the name or number of the record where the tag belongs. The
        optional data_type arguments is needed when the tag is unknown in the
        internal libraries, and used to decode the data. """
    
    if (self.iptc):
      return self.iptc.getTag(tag, record, data_type)
    return False

  def setIPTCTag(self, tag, payload = None, record = None, check = True, data_type = None, count = None, data = None):
    """ Set the specified IPTC tag name or number. Usually the payload parameter
        specifies the unencoded payload that needs to be set. Alternatively,
        encoded payload may be specified with the data parameter. The optional 
        record parameter specifies the name or number of the record where the
        tag belongs.
        If the tag is unknown, a KeyError is raised. If you still want to set
        the tag, check can be set to False. In this case, a record needs to be 
        specified to store the tag in and a data type for the format.
        Additionaly, if a payload is specified, an optional data count may be
        given for sanity checking.
    """
        
    if (self.iptc):
      self.iptc.setTag(tag, payload, record, check, data_type, count, data)

  def appendIPTCTag(self, tag, payload, record = None):
    """ Append the payload to the alreadyd defined IPTC tags with the specified
        name or number. The optional record parameter specifies the name or
        number of the record where the tag belongs. """
        
    if (self.iptc):
      self.iptc.appendTag(tag, payload, record = record)
      
  def delIPTCTag(self, tag, record = None):
    """ Remove the IPTC tag or tags with the specified name or number. The 
        optional record parameter specifies the name or number of the record
        where the tag belongs. """
        
    if (self.iptc):
      self.iptc.removeTag(tag, record)