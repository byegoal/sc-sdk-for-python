import sys
import hmac
import hashlib
import base64
import urllib2
import xml
import ConfigParser
import time
import logging
from tomcrypt import rsa
from xml.dom.minidom import parse, parseString

from sclib.sc.connection import SCConnection

LOG_LEVEL = "DEBUG"
REALM = "securecloud@trend.com"

# you need to configure the following
BASE_URL = "https://mapi_server.securecloud.com:8443/broker/api.svc"
BROKER_NAME = "mapi_test"
BROKER_PASS = "EWv6yqULCl"
USER_NAME = "shaodanny@gmail.com"
USER_PASS = "P@ssw0rd@123"

logging.basicConfig(level=LOG_LEVEL)


class broker_api:

    def __init__(self):
        self.base_url = BASE_URL

        self.user_name = USER_NAME
        self.user_pass = USER_PASS
        self.broker = BROKER_NAME
        self.broker_passphrase = BROKER_PASS
        self.realm = REALM
        self.session_token = self.basic_auth()

    # ----- help function start -----

    def getText(self, node):
        rc = ""

        if node.nodeType == node.ELEMENT_NODE:
            if node.hasChildNodes():
                nodelist = node.childNodes
                for node in nodelist:
                    if node.nodeType == node.TEXT_NODE:
                        rc = rc + node.data
        elif node.hasChildNodes():
            nodelist = node.childNodes
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc = rc + node.data

        return rc

    def nice_format(self, input):
        xmlstr = parseString(input)
        pretty_res = xmlstr.toprettyxml()

        return pretty_res

    def check_existing_node(self, nodes, id):

        for node in nodes:
            current_id = node.getAttribute("id")
            if(current_id == id):
                return True

        return False

    def get_node(self, nodes, id):

        for node in nodes:
            current_id = node.getAttribute("id")
            if(current_id == id):
                return node

    # ----- help function ends

    def basic_auth(self):

        # get server's public key
        pubkey = self.get_certificate()
        if not pubkey:
            return False

        # encrypt user password
        key = rsa.Key(pubkey)
        pub = key.public
        #print pub.as_string()

        password = bytes(self.user_pass)
        encrypted_password = pub.encrypt(password, None, "sha256", "oaep")
        encrypted_password = base64.b64encode(encrypted_password)

        req_xml = """<?xml version="1.0" encoding="utf-8"?><authentication xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" id="" data="%s" accountId="" />""" % (encrypted_password)
        logging.debug(req_xml)

        auth_url = self.base_url+ '/userBasicAuth/' + self.user_name + "?tenant="
        logging.debug(auth_url)
        pwd_mgr = urllib2.HTTPPasswordMgr()
        pwd_mgr.add_password(self.realm, auth_url, self.broker, self.broker_passphrase)
        opener = urllib2.build_opener()
        opener.add_handler(urllib2.HTTPDigestAuthHandler(pwd_mgr))

        req = urllib2.Request(auth_url)
        req.add_header('Content-Type', 'application/xml; charset=utf-8')
        req.add_header('BrokerName', self.broker)
        req.add_data(req_xml)

        try:
            sc_get_req = opener.open(req)
        except urllib2.HTTPError, e:
            logging.error(e)
            return False
        except urllib2.URLError, e:
            logging.error(e)
            return False

        res = sc_get_req.read()
        #logging.debug(res)

        xmldata = xml.dom.minidom.parseString(res)
        auth_result = xmldata.getElementsByTagName("authenticationResult")[0]
        session_token = auth_result.attributes["token"].value.strip()
        logging.debug("session token : %s" % session_token)

        return session_token


    def get_certificate(self):
        logging.debug("start get_certificate")
        
        auth_url = self.base_url + "/PublicCertificate/"

        req_xml = """<?xml version="1.0" encoding="utf-8"?><certificateRequest xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" version="2" />""" 


        pwd_mgr = urllib2.HTTPPasswordMgr()
        pwd_mgr.add_password(self.realm, auth_url, self.broker, self.broker_passphrase)
        opener = urllib2.build_opener()
        opener.add_handler(urllib2.HTTPDigestAuthHandler(pwd_mgr))

        req = urllib2.Request(auth_url)
        req.add_header('Content-Type', 'application/xml; charset=utf-8')
        req.add_header('BrokerName', self.broker)

        try:
            sc_get_req = opener.open(req)
        except urllib2.HTTPError, e:
            logging.error(e)
            return False
        except urllib2.URLError, e:
            logging.error(e)
            return False

        res = sc_get_req.read()
        logging.debug(res)

        try:
            xmldata = xml.dom.minidom.parseString(res)
            certificate_response = xmldata.getElementsByTagName("certificateResponse")[0]
            certificate_list = certificate_response.getElementsByTagName("certificateList")[0]
            certificate_node = certificate_response.getElementsByTagName("certificate")[0]
            certificate = self.getText(certificate_node)
            certificate = """-----BEGIN RSA PUBLIC KEY-----\n%s\n-----END RSA PUBLIC KEY-----\n""" % (certificate)
            certificate = str(certificate)
            #print certificate
        except Exception, e:
            logging.error(e)
            return False

        logging.debug("end get_certificate")        
        return certificate


    def sc_request(self, resource='', method='get', data=''):

        logging.debug("Start sc_request")

        #if not self.session_token:
        #    self.session_token = self.basic_auth()



        pwd_mgr = urllib2.HTTPPasswordMgr()
        api_url = self.base_url+'/'+resource+'/'
        pwd_mgr.add_password(self.realm, api_url, self.broker, self.broker_passphrase)
        opener = urllib2.build_opener()
        opener.add_handler(urllib2.HTTPDigestAuthHandler(pwd_mgr))

        req = urllib2.Request(api_url)

        logging.debug("url:%s" % (api_url))

        if method == 'post' and data != '':
            logging.debug(data)
            req.add_data(data)
        elif method == 'delete':
            req.get_method = lambda: 'DELETE'
        else:
            pass

        req.add_header('Content-Type', 'application/xml; charset=utf-8')
        req.add_header('BrokerName', self.broker)
        req.add_header('X-UserSession', self.session_token)

        try:
            sc_get_req = opener.open(req)
        except urllib2.HTTPError, e:
            logging.error(e)
            return False

        rawstr = sc_get_req.read()

        logging.debug("End sc_request")

        if(method == "delete"):
            if(rawstr == ""):
                return True
            else:
                return False
        else:
            return rawstr


    # ---------------------------------------------------------------------


    # image and device
    def listAllDevices(self):
        result = self.sc_request(resource='device')
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    def getDevice(self, device_id):
        result = self.sc_request(resource='device/'+device_id)
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    def listAllImages(self):
        result = self.sc_request(resource='image')
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    def getImage(self, image_id):
        result = self.sc_request(resource='image/'+image_id)
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    # policy
    def listAllSecurityGroups(self):
        result = self.sc_request(resource='securityGroup')
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    def getSecurityGroup(self, sg_id):
        result = self.sc_request(resource='securityGroup/'+sg_id)
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata

    def updateSecurityGroup(self, sg_id, sg_data):
        result = self.sc_request(resource='securityGroup/'+sg_id, method="post", data=sg_data)
        if not result:
            return False
        logging.debug(result)
        xmldata = xml.dom.minidom.parseString(result)

        return xmldata


if __name__ == '__main__':

    connection = SCConnection()
    logging.debug(connection.session_token)


    #get the device ID from portal
    portal_device_id_list = ["gcloud-image2-dev1","gcloud-image2-dev2"]
    retire_device_id_list = []

    #find out the device ID from all devices
    devices_xml = connection.listAllDevices()
    device_list = devices_xml.getElementsByTagName("deviceList")[0]
    devices = device_list.getElementsByTagName("device")

    for portal_device_id in portal_device_id_list:
        for device in devices:
            current_device_id = device.attributes["id"].value.strip()
            logging.debug("current_device_id:%s" % current_device_id)
            
            if portal_device_id == current_device_id:
                retire_device_id_list.append(current_device_id)


    #get the image ID from portal
    portal_image_id = "gcloud-image2"
    retire_image_id = ""

    #find out the image ID from all images    
    images_xml = connection.listAllImages()
    image_list = images_xml.getElementsByTagName("imageList")[0]
    images = image_list.getElementsByTagName("image")

    for image in images:
        current_image_id = image.attributes["id"].value.strip()
        logging.debug("current_image_id:%s" % current_image_id)

        if portal_image_id == current_image_id:
            retire_image_id = current_image_id


    # get retire policy msuid
    retire_policy_name = "retire_policy"
    retire_policy_msuid = ""

    policy_xml = connection.listAllSecurityGroups()
    policy_list = policy_xml.getElementsByTagName("securityGroupList")[0]
    policies = policy_list.getElementsByTagName("securityGroup")

    for policy in policies:
        current_policy_name = policy.attributes["name"].value.strip()
        logging.debug("current_policy_name:%s" % current_policy_name)
        current_policy_id = policy.attributes["id"].value.strip()
        logging.debug("current_policy_id:%s" % current_policy_id)

        if current_policy_name == retire_policy_name:
            retire_policy_msuid = current_policy_id


    # get retire policy data
    retire_policy_list = connection.getSecurityGroup(retire_policy_msuid)
    retire_policy = retire_policy_list.getElementsByTagName("securityGroup")[0]

    # add image to the retire policy
    try:
        is_existing_image = False        
        retire_image_list = retire_policy.getElementsByTagName("imageList")[0]
        retire_images = retire_policy.getElementsByTagName("image")
        for image in retire_images:
            current_image_id = image.attributes["id"].value.strip()
            logging.debug("current_image_id:%s" % current_image_id)
            if current_image_id == retire_image_id:
                is_existing_image = True
    except Exception, err:
        logging.error("The image list may not exist")
        retire_image_list = retire_policy_list.createElement("imageList")
        retire_policy.appendChild(retire_image_list)
        
    if not is_existing_image:
        new_image_node = retire_policy_list.createElement("image")
        new_image_node.setAttribute("id", retire_image_id)
        retire_image_list.appendChild(new_image_node)

    # add device to the retire policy
    for retire_device_id in retire_device_id_list:
        try:
            is_existing_device = False        
            retire_device_list = retire_policy.getElementsByTagName("deviceList")[0]
            retire_devices = retire_policy.getElementsByTagName("device")
            for device in retire_devices:
                current_device_id = device.attributes["id"].value.strip()
                logging.debug("current_device_id:%s" % current_device_id)
                if current_device_id == retire_device_id:
                    is_existing_device = True
        except Exception, err:
            logging.error("The device list may not exist")
            retire_device_list = retire_policy_list.createElement("deviceList")
            retire_policy.appendChild(retire_device_list)
            
        if not is_existing_device:
            new_device_node = retire_policy_list.createElement("device")
            new_device_node.setAttribute("id", retire_device_id)
            retire_device_list.appendChild(new_device_node)



    update_policy_data = retire_policy_list.toxml()
    logging.debug(update_policy_data)

    updated_xml = connection.updateSecurityGroup(retire_policy_msuid, update_policy_data)