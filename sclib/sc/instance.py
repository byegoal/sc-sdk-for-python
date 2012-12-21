# Copyright (c) 2012 Trend Micro, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

from sclib.resultset import ResultSet
from sclib.sc.scobject import SCObject
from sclib.sc.device import Device
from sclib.sc.provider import Provider
from xml.etree import ElementTree

class Instance(SCObject):
    def __init__(self, connection=None):
        pass
    
class VirtualMachine(SCObject):
    #===========================================================================
    # present vm object
    #===========================================================================
    
    # Required fields
    Required = ['imageGUID', 'imageName', 'autoProvision', 'SecurityGroupGUID', 'imageDescription']
    
    # Present valid vm object attributes, not inner objects
    ValidAttributes = [ 'SecurityGroupGUID', 'autoProvision',
                        'detectedKeyCount', 'encryptedDeviceCount', 'encryptingDeviceCount', 'href',
                        'imageGUID', 'imageID', 'imageName', 
                        'instanceGUID','instanceID', 'lastModified', 
                        'nonEncryptedDeviceCount', 'pendingDeviceCount']
    
    
    def __init__(self, connection):
        SCObject.__init__(self, connection)
        #=======================================================================
        # Attributes
        #=======================================================================
        self.SecurityGroupGUID = None
        self.autoProvision = None
        self.detectedKeyCount = None
        self.encryptedDeviceCount = None
        self.encryptingDeviceCount = None
        self.href = None
        self.imageGUID = None
        self.imageID = None
        self.imageName = None
        self.instanceGUID = None
        self.instanceID = None
        self.lastModified = None
        self.nonEncryptedDeviceCount = None
        self.pendingDeviceCount = None
        #=======================================================================
        # elements
        #=======================================================================
        self.imageDescription = None
        # Provider object
        self.provider = None
        # Platform object
        self.platform = None
        # SCAgent object
        self.agent = None
        # Device object
        self.devices = None
        
        pass

    def startElement(self, name, attrs, connection):
        ret = SCObject.startElement(self, name, attrs, connection)
        if ret is not None:
            return ret
        
        if name == 'vm':
            # keep all attributes
            for key, value in attrs.items():
                setattr(self, key, value)
        elif name == 'provider':
            self.provider = Provider(connection)
            self.provider.startElement(name, attrs, connection)
            return self.provider
        elif name == 'securecloudAgent':
            self.agent = SCAgent(connection)
            self.agent.startElement(name, attrs, connection)
            return self.agent
        elif name == 'devices':
            self.devices = ResultSet([('device', Device)])
            self.devices.name = name
            return self.devices
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'platform':
            self.platform = value
        elif name == 'imageDescription':
            self.imageDescription = value
        else:
            setattr(self, name, value)
            
    def buildElements(self, elements=None):

        vm = ElementTree.Element('vm')
        
        if elements:
            # build attributes
            for e in elements:
                if e in self.ValidAttributes:
                    vm.attrib[e] = getattr(self, e)
                elif e == 'imageDescription':
                    description = ElementTree.SubElement(vm, "imageDescription")
                    description.text = self.imageDescription
                elif e == 'provider':
                    vm.append( self.provider.buildElements() )
                elif e == 'devices':
                    vm.append( self.devices.buildElements() )
                elif e == 'securecloudAgent':
                    vm.append( self.agents.buildElements() )
        else:
            # build attributes
            for attr in self.ValidAttributes:
                vm.attrib[attr] = getattr(self, attr)
            description = ElementTree.SubElement(vm, "imageDescription")
            description.text = self.imageDescription
            # append inner objects
            vm.append( self.provider.buildElements() )
            vm.append( self.devices.buildElements() )
            vm.append( self.agents.buildElements() )
            
        return vm

    #===========================================================================
    # functions start 
    #===========================================================================
    def update(self, updates=None):
        action = 'vm/%s/' % self.imageGUID
        updateFiels = updates
        if not updateFiels:
            # default update fields
            updateFields = ['imageGUID', 'imageName', 'autoProvision', 'SecurityGroupGUID', 'imageDescription']
            
        data = ElementTree.tostring( self.buildElements(updateFields) )
        return self.connection.get_object(action, {}, VirtualMachine, data=data, method='POST')
    
    def delete(self):
        action = 'vm/%s/' % self.imageGUID
        return self.connection.get_status(action, {}, method='DELETE')
    
    def deleteDevice(self, deviceID):
        action = 'vm/%s/device/%s/' % (self.imageGUID, deviceID)
        return self.connection.get_status(action, {}, method='DELETE')
        


class SCAgent(SCObject):
    ValidAttributes = ['agentStatus', 'agentVersion']
    def __init__(self, connection):
        # member information
        self.agentStatus = None
        self.agentVersion = None

    def startElement(self, name, attrs, connection):
        ret = SCObject.startElement(self, name, attrs, connection)
        if ret is not None:
            return ret
        
        if name == 'securecloudAgent':
            self.agentStatus = attrs['agentStatus']
            self.agentVersion = attrs['agentVersion']
        else:
            return None

    def endElement(self, name, value, connection):
        setattr(self, name, value)
            
    def buildElements(self, elements=None):
        agent = ElementTree.Element('agent')
        if self.agentStatus: agent.attrib['agentStatus'] = self.agentStatus
        if self.agentVersion: agent.attrib['agentVersion'] = self.agentVersion
        return agent

    
    