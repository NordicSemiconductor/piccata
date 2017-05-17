"""
Copyright (c) 2012 Maciej Wasilak <http://sixpinetrees.blogspot.com/>
              2017 Robert Lubos

Implementation of the lowest-level Resource class.
"""

import message
from constants import *
from itertools import chain
from types import NoResource, UnallowedMethod, UnsupportedMethod

# TODO This code might need some polishing if it's going to be used.

class CoapResource(object):
    """CoAP-accessible resource."""

    server = None

    def __init__(self):
        """Initialize.
        """
        self.children = {}
        self.params = {}
        self.visible = False
        self.observers = {} # (address, token) -> observation

    observable = False
    observe_index = 0
    isLeaf = 0

    ### Abstract Collection Interface

    def listStaticNames(self):
        return self.children.keys()

    def listStaticEntities(self):
        return self.children.items()

    def listNames(self):
        return self.listStaticNames() + self.listDynamicNames()

    def listEntities(self):
        return self.listStaticEntities() + self.listDynamicEntities()

    def listDynamicNames(self):
        return []

    def listDynamicEntities(self, request=None):
        return []

    def getStaticEntity(self, name):
        return self.children.get(name)

    def getDynamicEntity(self, name, request):
        if name not in self.children:
            return self.getChild(name, request)
        else:
            return None

    def delEntity(self, name):
        del self.children[name]

    def reallyPutEntity(self, name, entity):
        self.children[name] = entity

    # Concrete HTTP interface

    def getChild(self, path, request):
        """
        Retrieve a 'child' resource from me.

        Implement this to create dynamic resource generation -- resources which
        are always available may be registered with self.putChild().

        This will not be called if the class-level variable 'isLeaf' is set in
        your subclass; instead, the 'postpath' attribute of the request will be
        left as a list of the remaining path elements.

        For example, the URL /foo/bar/baz will normally be::

          | site.resource.getChild('foo').getChild('bar').getChild('baz').

        However, if the resource returned by 'bar' has isLeaf set to true, then
        the getChild call will never be made on it.

        @param path: a string, describing the child

        @param request: a twisted.web.server.Request specifying meta-information
                        about the request that is being made for this child.
        """
        raise NoResource

    def getChildWithDefault(self, path, request):
        """
        Retrieve a static or dynamically generated child resource from me.

        First checks if a resource was added manually by putChild, and then
        call getChild to check for dynamic resources. Only override if you want
        to affect behaviour of all child lookups, rather than just dynamic
        ones.

        This will check to see if I have a pre-registered child resource of the
        given name, and call getChild if I do not.
        """
        if path in self.children:
            return self.children[path]
        return self.getChild(path, request)

    def putChild(self, path, child):
        """
        Register a static child.

        You almost certainly don't want '/' in your path. If you
        intended to have the root of a folder, e.g. /foo/, you want
        path to be ''.
        """
        self.children[path] = child
        child.server = self.server

    def render(self, request):
        """
        Render a given resource. Calls a handler for respective request code in format render_CODE.

        The render method shall accept one argument with a request message. An example render method:
            rended_GET(request)

        Args:
            request (coap.message.Message) A request for handling.
        """
        if request.code not in requests:
            raise UnsupportedMethod()
        m = getattr(self, 'render_' + requests[request.code], None)
        if not m:
            raise UnallowedMethod()
        return m(request)

    def addParam(self, param):
        self.params.setdefault(param.name, []).append(param)

    def deleteParam(self, name):
        if name in self.params:
            self.params.pop(name)

    def getParam(self, name):
        return self.params.get(name)

    def encode_params(self):
        data = [""]
        param_list = chain.from_iterable(sorted(self.params.values(), key=lambda x: x[0].name))
        for param in param_list:
            data.append(param.encode())
        return (';'.join(data))

    def generateResourceList(self, data, path=""):
        params = self.encode_params() + (";obs" if self.observable else "")
        if self.visible is True:
            if path is "":
                data.append('</>' + params)
            else:
                data.append('<' + path + '>' + params)
        for key in self.children:
            self.children[key].generateResourceList(data, path + "/" + key)


class LinkParam(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def decode(self, rawdata):
        pass

    def encode(self):
        return '%s="%s"' % (self.name, self.value)


class CoapEndpoint(object):

    def __init__(self, root_resource):
        """Initialize CoAP endpoint.

        Args:
            root_resource (coap.resource.CoapResource) Root resource of the resource tree.
        """
        self.root = root_resource

    def get_resource_for(self, request):
        """Get a resource for a request.

        This iterates through the resource heirarchy, calling getChildWithDefault on each resource
        it finds for a path element, stopping when it hits an element where isLeaf is true.

        Args:
            request (coap.message.Message) A request containing the Uri path to search for.
        """
        resource = self.root
        postpath = request.opt.uri_path

        while postpath and not resource.isLeaf:
            pathElement = postpath.pop(0)
            resource = resource.getChildWithDefault(pathElement, request)
        return resource


class ResoureManager(object):

    def __init__(self, endpoint):
        """Initialize the resource manager.

        Args:
            endpoint (coap.resource.coapEndpoint): An endpoint containing the resource tree.
        """
        self.endpoint = endpoint

    def receive_request(self, request):
        """Function for handling requests.

        This function will be called by the CoAP object after registration of ResourceManager object.

        Args:
            request (coap.message.Message): Request received.

        Returns:
            A response to send back. None if no response shall be sent.
        """
        response = None

        try:
            resource = self.endpoint.get_resource_for(request)
            response = resource.render(request)
        except NoResource:
            response = message.Message.AckMessage(request, code=NOT_FOUND, payload="Error: Resource not found!")
        except UnallowedMethod:
            response = message.Message.AckMessage(request, code=METHOD_NOT_ALLOWED, payload="Error: Method not allowed!")
        except UnsupportedMethod:
            response = message.Message.AckMessage(request, code=METHOD_NOT_ALLOWED, payload="Error: Method not recognized!")

        return response

