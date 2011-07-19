/* To whom it may concern ....

I cobbled the following together as a quick and nasty JSON-RPC v2 client
for use with the Python jsonrpclib. Believe it or not, there aren't any
notify call supporting Javascript clients out there (that I could find at
least), so the below solves a useful problem.

The below comes from json.org (for JSON.stringify and JSON.parse where the
browser does not natively support these). And a heavily modified JSON-RPC
client taken from http://www.jabsorb.org which cuts out the Java support,
uses native JSON instead of its own custom parser which used eval() (NAUGHTY!),
adds support for notify ops which are sent async, and says it supports
JSON-RPC v2.

The below is fairly swift for very large data transfers. In fact, right now
it can easily overload Python's jsonrpclib even when it's using ujson :)
I'd say you might have to PyPy your Python to catch up.

Best of luck to anyone using this. And no warranties express or implied!

Niall Douglas
http://www.nedproductions.biz/
July 2011
*/


/*
http://www.JSON.org/json2.js
2011-02-23

Public Domain.

NO WARRANTY EXPRESSED OR IMPLIED. USE AT YOUR OWN RISK.

See http://www.JSON.org/js.html


This code should be minified before deployment.
See http://javascript.crockford.com/jsmin.html

USE YOUR OWN COPY. IT IS EXTREMELY UNWISE TO LOAD CODE FROM SERVERS YOU DO
NOT CONTROL.


This file creates a global JSON object containing two methods: stringify
and parse.

JSON.stringify(value, replacer, space)
value any JavaScript value, usually an object or array.

replacer an optional parameter that determines how object
values are stringified for objects. It can be a
function or an array of strings.

space an optional parameter that specifies the indentation
of nested structures. If it is omitted, the text will
be packed without extra whitespace. If it is a number,
it will specify the number of spaces to indent at each
level. If it is a string (such as '\t' or '&nbsp;'),
it contains the characters used to indent at each level.

This method produces a JSON text from a JavaScript value.

When an object value is found, if the object contains a toJSON
method, its toJSON method will be called and the result will be
stringified. A toJSON method does not serialize: it returns the
value represented by the name/value pair that should be serialized,
or undefined if nothing should be serialized. The toJSON method
will be passed the key associated with the value, and this will be
bound to the value

For example, this would serialize Dates as ISO strings.

Date.prototype.toJSON = function (key) {
function f(n) {
// Format integers to have at least two digits.
return n < 10 ? '0' + n : n;
}

return this.getUTCFullYear() + '-' +
f(this.getUTCMonth() + 1) + '-' +
f(this.getUTCDate()) + 'T' +
f(this.getUTCHours()) + ':' +
f(this.getUTCMinutes()) + ':' +
f(this.getUTCSeconds()) + 'Z';
};

You can provide an optional replacer method. It will be passed the
key and value of each member, with this bound to the containing
object. The value that is returned from your method will be
serialized. If your method returns undefined, then the member will
be excluded from the serialization.

If the replacer parameter is an array of strings, then it will be
used to select the members to be serialized. It filters the results
such that only members with keys listed in the replacer array are
stringified.

Values that do not have JSON representations, such as undefined or
functions, will not be serialized. Such values in objects will be
dropped; in arrays they will be replaced with null. You can use
a replacer function to replace those with JSON values.
JSON.stringify(undefined) returns undefined.

The optional space parameter produces a stringification of the
value that is filled with line breaks and indentation to make it
easier to read.

If the space parameter is a non-empty string, then that string will
be used for indentation. If the space parameter is a number, then
the indentation will be that many spaces.

Example:

text = JSON.stringify(['e', {pluribus: 'unum'}]);
// text is '["e",{"pluribus":"unum"}]'


text = JSON.stringify(['e', {pluribus: 'unum'}], null, '\t');
// text is '[\n\t"e",\n\t{\n\t\t"pluribus": "unum"\n\t}\n]'

text = JSON.stringify([new Date()], function (key, value) {
return this[key] instanceof Date ?
'Date(' + this[key] + ')' : value;
});
// text is '["Date(---current time---)"]'


JSON.parse(text, reviver)
This method parses a JSON text to produce an object or array.
It can throw a SyntaxError exception.

The optional reviver parameter is a function that can filter and
transform the results. It receives each of the keys and values,
and its return value is used instead of the original value.
If it returns what it received, then the structure is not modified.
If it returns undefined then the member is deleted.

Example:

// Parse the text. Values that look like ISO date strings will
// be converted to Date objects.

myData = JSON.parse(text, function (key, value) {
var a;
if (typeof value === 'string') {
a =
/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)Z$/.exec(value);
if (a) {
return new Date(Date.UTC(+a[1], +a[2] - 1, +a[3], +a[4],
+a[5], +a[6]));
}
}
return value;
});

myData = JSON.parse('["Date(09/09/2001)"]', function (key, value) {
var d;
if (typeof value === 'string' &&
value.slice(0, 5) === 'Date(' &&
value.slice(-1) === ')') {
d = new Date(value.slice(5, -1));
if (d) {
return d;
}
}
return value;
});


This is a reference implementation. You are free to copy, modify, or
redistribute.
*/

/*jslint evil: true, strict: false, regexp: false */

/*members "", "\b", "\t", "\n", "\f", "\r", "\"", JSON, "\\", apply,
call, charCodeAt, getUTCDate, getUTCFullYear, getUTCHours,
getUTCMinutes, getUTCMonth, getUTCSeconds, hasOwnProperty, join,
lastIndex, length, parse, prototype, push, replace, slice, stringify,
test, toJSON, toString, valueOf
*/


// Create a JSON object only if one does not already exist. We create the
// methods in a closure to avoid creating global variables.

var JSON;
if (!JSON) {
    JSON = {};
}

(function () {
    "use strict";

    function f(n) {
        // Format integers to have at least two digits.
        return n < 10 ? '0' + n : n;
    }

    if (typeof Date.prototype.toJSON !== 'function') {

        Date.prototype.toJSON = function (key) {

            return isFinite(this.valueOf()) ?
                this.getUTCFullYear() + '-' +
                f(this.getUTCMonth() + 1) + '-' +
                f(this.getUTCDate()) + 'T' +
                f(this.getUTCHours()) + ':' +
                f(this.getUTCMinutes()) + ':' +
                f(this.getUTCSeconds()) + 'Z' : null;
        };

        String.prototype.toJSON =
            Number.prototype.toJSON =
            Boolean.prototype.toJSON = function (key) {
                return this.valueOf();
            };
    }

    var cx = /[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,
        escapable = /[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,
        gap,
        indent,
        meta = { // table of character substitutions
            '\b': '\\b',
            '\t': '\\t',
            '\n': '\\n',
            '\f': '\\f',
            '\r': '\\r',
            '"' : '\\"',
            '\\': '\\\\'
        },
        rep;


    function quote(string) {

// If the string contains no control characters, no quote characters, and no
// backslash characters, then we can safely slap some quotes around it.
// Otherwise we must also replace the offending characters with safe escape
// sequences.

        escapable.lastIndex = 0;
        return escapable.test(string) ? '"' + string.replace(escapable, function (a) {
            var c = meta[a];
            return typeof c === 'string' ? c :
                '\\u' + ('0000' + a.charCodeAt(0).toString(16)).slice(-4);
        }) + '"' : '"' + string + '"';
    }


    function str(key, holder) {

// Produce a string from holder[key].

        var i, // The loop counter.
            k, // The member key.
            v, // The member value.
            length,
            mind = gap,
            partial,
            value = holder[key];

// If the value has a toJSON method, call it to obtain a replacement value.

        if (value && typeof value === 'object' &&
                typeof value.toJSON === 'function') {
            value = value.toJSON(key);
        }

// If we were called with a replacer function, then call the replacer to
// obtain a replacement value.

        if (typeof rep === 'function') {
            value = rep.call(holder, key, value);
        }

// What happens next depends on the value's type.

        switch (typeof value) {
        case 'string':
            return quote(value);

        case 'number':

// JSON numbers must be finite. Encode non-finite numbers as null.

            return isFinite(value) ? String(value) : 'null';

        case 'boolean':
        case 'null':

// If the value is a boolean or null, convert it to a string. Note:
// typeof null does not produce 'null'. The case is included here in
// the remote chance that this gets fixed someday.

            return String(value);

// If the type is 'object', we might be dealing with an object or an array or
// null.

        case 'object':

// Due to a specification blunder in ECMAScript, typeof null is 'object',
// so watch out for that case.

            if (!value) {
                return 'null';
            }

// Make an array to hold the partial results of stringifying this object value.

            gap += indent;
            partial = [];

// Is the value an array?

            if (Object.prototype.toString.apply(value) === '[object Array]') {

// The value is an array. Stringify every element. Use null as a placeholder
// for non-JSON values.

                length = value.length;
                for (i = 0; i < length; i += 1) {
                    partial[i] = str(i, value) || 'null';
                }

// Join all of the elements together, separated with commas, and wrap them in
// brackets.

                v = partial.length === 0 ? '[]' : gap ?
                    '[\n' + gap + partial.join(',\n' + gap) + '\n' + mind + ']' :
                    '[' + partial.join(',') + ']';
                gap = mind;
                return v;
            }

// If the replacer is an array, use it to select the members to be stringified.

            if (rep && typeof rep === 'object') {
                length = rep.length;
                for (i = 0; i < length; i += 1) {
                    if (typeof rep[i] === 'string') {
                        k = rep[i];
                        v = str(k, value);
                        if (v) {
                            partial.push(quote(k) + (gap ? ': ' : ':') + v);
                        }
                    }
                }
            } else {

// Otherwise, iterate through all of the keys in the object.

                for (k in value) {
                    if (Object.prototype.hasOwnProperty.call(value, k)) {
                        v = str(k, value);
                        if (v) {
                            partial.push(quote(k) + (gap ? ': ' : ':') + v);
                        }
                    }
                }
            }

// Join all of the member texts together, separated with commas,
// and wrap them in braces.

            v = partial.length === 0 ? '{}' : gap ?
                '{\n' + gap + partial.join(',\n' + gap) + '\n' + mind + '}' :
                '{' + partial.join(',') + '}';
            gap = mind;
            return v;
        }
    }

// If the JSON object does not yet have a stringify method, give it one.

    if (typeof JSON.stringify !== 'function') {
        JSON.stringify = function (value, replacer, space) {

// The stringify method takes a value and an optional replacer, and an optional
// space parameter, and returns a JSON text. The replacer can be a function
// that can replace values, or an array of strings that will select the keys.
// A default replacer method can be provided. Use of the space parameter can
// produce text that is more easily readable.

            var i;
            gap = '';
            indent = '';

// If the space parameter is a number, make an indent string containing that
// many spaces.

            if (typeof space === 'number') {
                for (i = 0; i < space; i += 1) {
                    indent += ' ';
                }

// If the space parameter is a string, it will be used as the indent string.

            } else if (typeof space === 'string') {
                indent = space;
            }

// If there is a replacer, it must be a function or an array.
// Otherwise, throw an error.

            rep = replacer;
            if (replacer && typeof replacer !== 'function' &&
                    (typeof replacer !== 'object' ||
                    typeof replacer.length !== 'number')) {
                throw new Error('JSON.stringify');
            }

// Make a fake root object containing our value under the key of ''.
// Return the result of stringifying the value.

            return str('', {'': value});
        };
    }


// If the JSON object does not yet have a parse method, give it one.

    if (typeof JSON.parse !== 'function') {
        JSON.parse = function (text, reviver) {

// The parse method takes a text and an optional reviver function, and returns
// a JavaScript value if the text is a valid JSON text.

            var j;

            function walk(holder, key) {

// The walk method is used to recursively walk the resulting structure so
// that modifications can be made.

                var k, v, value = holder[key];
                if (value && typeof value === 'object') {
                    for (k in value) {
                        if (Object.prototype.hasOwnProperty.call(value, k)) {
                            v = walk(value, k);
                            if (v !== undefined) {
                                value[k] = v;
                            } else {
                                delete value[k];
                            }
                        }
                    }
                }
                return reviver.call(holder, key, value);
            }


// Parsing happens in four stages. In the first stage, we replace certain
// Unicode characters with escape sequences. JavaScript handles many characters
// incorrectly, either silently deleting them, or treating them as line endings.

            text = String(text);
            cx.lastIndex = 0;
            if (cx.test(text)) {
                text = text.replace(cx, function (a) {
                    return '\\u' +
                        ('0000' + a.charCodeAt(0).toString(16)).slice(-4);
                });
            }

// In the second stage, we run the text against regular expressions that look
// for non-JSON patterns. We are especially concerned with '()' and 'new'
// because they can cause invocation, and '=' because it can cause mutation.
// But just to be safe, we want to reject all unexpected forms.

// We split the second stage into 4 regexp operations in order to work around
// crippling inefficiencies in IE's and Safari's regexp engines. First we
// replace the JSON backslash pairs with '@' (a non-JSON character). Second, we
// replace all simple value tokens with ']' characters. Third, we delete all
// open brackets that follow a colon or comma or that begin the text. Finally,
// we look to see that the remaining characters are only whitespace or ']' or
// ',' or ':' or '{' or '}'. If that is so, then the text is safe for eval.

            if (/^[\],:{}\s]*$/
                    .test(text.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, '@')
                        .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, ']')
                        .replace(/(?:^|:|,)(?:\s*\[)+/g, ''))) {

// In the third stage we use the eval function to compile the text into a
// JavaScript structure. The '{' operator is subject to a syntactic ambiguity
// in JavaScript: it can begin a block or an object literal. We wrap the text
// in parens to eliminate the ambiguity.

                j = eval('(' + text + ')');

// In the optional fourth stage, we recursively walk the new structure, passing
// each name/value pair to a reviver function for possible transformation.

                return typeof reviver === 'function' ?
                    walk({'': j}, '') : j;
            }

// If the text is not JSON parseable, then a SyntaxError is thrown.

            throw new SyntaxError('JSON.parse');
        };
    }
}());













/*
 * jabsorb - a Java to JavaScript Advanced Object Request Broker
 * http://www.jabsorb.org
 *
 * Copyright 2007-2009 The jabsorb team
 * Copyright (c) 2005 Michael Clark, Metaparadigm Pte Ltd
 * Copyright (c) 2003-2004 Jan-Klaas Kollhof
 *
 * This code is based on original code from the json-rpc-java library
 * which was originally based on Jan-Klaas' JavaScript o lait library
 * (jsolait).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

/**
 * JSONRpcClient constructor
 *
 * @param callback|methods - the function to call once the rpc list methods has completed.
 *                   if this argument is omitted completely, then the JSONRpcClient
 *                   is constructed synchronously.
 *                   if this arguement is an array then it is the list of methods
 *                   that can be invoked on the server (and the server will not
 *                   be queried for that information)
 *
 * @param serverURL - path to JSONRpcServlet on server.
 * @param user
 * @param pass
 * @param objectID
 * @param javaClass
 * @param JSONRPCType
 *
 */
function JSONRpcClient()
{
  var arg_shift = 0, req, _function, methods, self, name, arg0type= (typeof arguments[0]), doListMethods=true;

  //If a call back is being used grab it
  if (arg0type === "function")
  {
    this.readyCB = arguments[0];
    arg_shift++;
  }
  // if it's an array then just do add methods directly
  else if (arguments[0] && arg0type === "object" && arguments[0].length)
  {
    this._addMethods(arguments[0]); // go ahead and add the methods directly
    arg_shift++;
    doListMethods=false;
  }

  //The next 3 args are passed to the http request
  this.serverURL = arguments[arg_shift];
  this.user = arguments[arg_shift + 1];
  this.pass = arguments[arg_shift + 2];
  this.objectID=0;

  if (doListMethods)
  {
    //Add the listMethods system methods
    this._addMethods(["system.listMethods"]);
    //Make the call to list the methods
    req = JSONRpcClient._makeRequest(this,"system.listMethods", []);
    //If a callback was added to the constructor, call it
    if(this.readyCB)
    {
      self = this;
      req.cb = function(result, e)
      {
         if(!e)
         {
           self._addMethods(result);
         }
         self.readyCB(result, e);
      };
    }

    if(!this.readyCB)
    {
      methods = JSONRpcClient._sendRequest(this,req);
      this._addMethods(methods);
    }
    else
    {
      JSONRpcClient.async_requests.push(req);
      JSONRpcClient.kick_async();
    }
  }
}

/**
 * Creates a new callable proxy (reference).
 *
 * @param objectID The id of the object as determined by the server
 * @param javaClass The package+classname of the object
 * @return a new callable proxy object
 */
JSONRpcClient.prototype.createCallableProxy=function(objectID,javaClass)
{
  var cp,req,methodNames,name,i;

  cp = new JSONRPCCallableProxy(objectID,javaClass);
  //Then add all the cached methods to it.
  for (name in JSONRpcClient.knownClasses[javaClass])
  {
    //Change the this to the object that will be calling it
    cp[name]=JSONRpcClient.bind(
      JSONRpcClient.knownClasses[javaClass][name],cp);
  }
  return cp;
};

/* JSONRpcClient constructor */

function JSONRPCCallableProxy()
{
    //A unique identifier which the identity hashcode of the object on the server, if this is a reference type
  this.objectID = arguments[0];
  //The full package+classname of the object
  this.javaClass = arguments[1];
  this.JSONRPCType = "CallableReference";
}

//This is a static variable that maps className to a map of functions names to
//calls, ie Map knownClasses<ClassName,Map<FunctionName,Function>>
JSONRpcClient.knownClasses = {};

/* JSONRpcCLient.Exception */
JSONRpcClient.Exception = function (errorObject)
{
  var m;
  for( var prop in errorObject)
  {
    if (errorObject.hasOwnProperty(prop))
    {
      this[prop] = errorObject[prop];
    }
  }
  if (this.trace)
  {
    m = this.trace.match(/^([^:]*)/);
    if (m)
    {
      this.name = m[0];
    }
  }
  if (!this.name)
  {
    this.name = "JSONRpcClientException";
  }
};

//Error codes that are the same as on the bridge
JSONRpcClient.Exception.CODE_REMOTE_EXCEPTION = 490;
JSONRpcClient.Exception.CODE_ERR_CLIENT = 550;
JSONRpcClient.Exception.CODE_ERR_PARSE = 590;
JSONRpcClient.Exception.CODE_ERR_NOMETHOD = 591;
JSONRpcClient.Exception.CODE_ERR_UNMARSHALL = 592;
JSONRpcClient.Exception.CODE_ERR_MARSHALL = 593;

JSONRpcClient.Exception.prototype = new Error();

JSONRpcClient.Exception.prototype.toString = function (code, msg)
{
  var str="";
  if(this.name)
  {
    str+=this.name;
  }
  if(this.message)
  {
    str+=": "+this.message;
  }
  if(str.length==0)
  {
    str="no exception information given";
  }
  return str;
};


/* Default top level exception handler */

JSONRpcClient.default_ex_handler = function (e)
{
  // unhandled exception thrown in jsonrpc handler
  var a,str="";
  for(a in e)
  {
    str+=a +"\t"+e[a]+"\n";
  }
  alert(str);
};


/* Client settable variables */

JSONRpcClient.toplevel_ex_handler = JSONRpcClient.default_ex_handler;
JSONRpcClient.profile_async = false;
JSONRpcClient.max_req_active = 1;
JSONRpcClient.requestId = 1;

// if this is true, circular references in the object graph are fixed up
// if this is false, circular references cause an exception to be thrown
JSONRpcClient.fixupCircRefs = false;

// if this is true, duplicate objects in the object graph are optimized
// if it's false, then duplicate objects are "re-serialized"
JSONRpcClient.fixupDuplicates = false;

/**
 * if true, java.util.Date object are unmarshalled to javascript dates
 * if false, no customized unmarshalling for dates is done
 */
JSONRpcClient.transformDates = false;

/**
 * Used to bind the this of the serverMethodCaller() (see below) which is to be
 * bound to the right object. This is needed as the serverMethodCaller is
 * called only once in createMethod and is then assigned to multiple
 * CallableReferences are created.
 */
JSONRpcClient.bind=function(functionName,context)
{
  return function() {
    return functionName.apply(context, arguments);
  };
};

/*
 * This creates a method that points to the serverMethodCaller and binds it
 * with the correct methodName.
 */
JSONRpcClient._createMethod = function (client,methodName, isnotify)
{
  //This function is what the user calls.
  //This function uses a closure on methodName to ensure that the function
  //always has the same name, but can take different arguments each call.
  //Each time it is added to an object this should be set with bind()
  var serverMethodCaller= function()
  {
    var args = [],
      callback;
    for (var i = 0; i < arguments.length; i++)
    {
      args.push(arguments[i]);
    }
    if (typeof args[0] == "function")
    {
      callback = args.shift();
    }
	//console.log("calling ", methodName, args, "callback=",callback, "isnotify=", isnotify);
    var req = JSONRpcClient._makeRequest(this, methodName, args, this.objectID,callback, isnotify);
    if (!callback)
    {
      return JSONRpcClient._sendRequest(client, req, isnotify);
    }
    else
    {
      //when there is a callback, add the req to the list
      JSONRpcClient.async_requests.push(req);
      JSONRpcClient.kick_async();
      return req.requestId;
    }
  };

  return serverMethodCaller;
};

/**
 * Creates a new object from the bridge. A callback may optionally be given as
 * the first argument to make this an async call.
 *
 * @param callback (optional)
 * @param constructorName The name of the class to create, which should be
 *   registered with JSONRPCBridge.registerClass()
 * @param _args The arguments the constructor takes
 * @return the new object if sync, the request id if async.
 */
JSONRpcClient.prototype.createObject = function ()
{
  var args = [],
      callback = null,
      constructorName,
      _args,
      req;
  for(var i=0;i<arguments.length;i++)
  {
    args.push(arguments[i]);
  }
  if(typeof args[0] == "function")
  {
    callback = args.shift();
  }
  constructorName=args[0]+".$constructor";
  _args=args[1];

  req = JSONRpcClient._makeRequest(this, constructorName, _args, 0,callback);
  if(callback === null)
  {
    return JSONRpcClient._sendRequest(this, req);
  }
  else
  {
    JSONRpcClient.async_requests.push(req);
    JSONRpcClient.kick_async();
    return req.requestId;
  }
};

JSONRpcClient.CALLABLE_REFERENCE_METHOD_PREFIX = ".ref";

/**
 * This is used to add a list of methods to this.
 * @param methodNames a list containing the names of the methods to add
 * @param dontAdd If this is set, methods wont actually added
 * @return the methods that were created
 */
JSONRpcClient.prototype._addMethods = function (methodNames,dontAdd)
{
  var name,
      obj,
      names,
      n,
      method,
      methods=[],
      javaClass,
      tmpNames,
      startIndex,
      endIndex;
  //Aha! It is a class, so create a entry for it.
  //This shouldn't get called twice on the same class so we can happily
  //overwrite it
  //if(javaClass){
  //  JSONRpcClient.knownClasses[javaClass]={};
  //}

  for (var i = 0; i < methodNames.length; i++)
  {
    obj = this;

    names = methodNames[i].split(".");
    startIndex=methodNames[i].indexOf("[");
    endIndex=methodNames[i].indexOf("]");
    if(
        (methodNames[i].substring(0,
          JSONRpcClient.CALLABLE_REFERENCE_METHOD_PREFIX.length)==
          JSONRpcClient.CALLABLE_REFERENCE_METHOD_PREFIX)
      &&(startIndex!=-1)&&(endIndex!=-1)&&(startIndex<endIndex))
    {
      javaClass=methodNames[i].substring(startIndex+1,endIndex);
    }
    else
    {
      //Create intervening objects in the path to the method name.
      //For example with the method name "system.listMethods", we first
      //create a new object called "system" and then add the "listMethod"
      //function to that object.
      for (n = 0; n < names.length - 1; n++)
      {
        name = names[n];
        if (obj[name])
        {
          obj = obj[name];
        }
        else
        {
          obj[name] = {};
          obj = obj[name];
        }
      }
    }
    //The last part of the name is the actual functionName
    name = names[names.length - 1];

    //Create the method

    if(javaClass)
    {
      method = JSONRpcClient._createMethod(this,name);
      if(!JSONRpcClient.knownClasses[javaClass])
      {
        JSONRpcClient.knownClasses[javaClass]={};
      }
      JSONRpcClient.knownClasses[javaClass][name]=method;
    }
    else
    {
      method = JSONRpcClient._createMethod(this,methodNames[i], false);
      notifymethod = JSONRpcClient._createMethod(this,methodNames[i], true);
      //If it doesn't yet exist and it is to be added to this
      if ((!obj[name])&&(!dontAdd))
      {
        obj[name]=JSONRpcClient.bind(method,this);
		if(!("_notify" in obj)) obj["_notify"]={};
        obj._notify[name]=JSONRpcClient.bind(notifymethod,this);
      }
      //maintain a list of all methods created so that methods[i]==methodNames[i]
      methods.push(method);
    }
    javaClass=null;
  }

  return methods;
};

JSONRpcClient._getCharsetFromHeaders = function (http)
{
  var contentType,
      parts,
      i;
  try
  {
    contentType = http.getResponseHeader("Content-type");
    parts = contentType.split(/\s*;\s*/);
    for (i = 0; i < parts.length; i++)
    {
      if (parts[i].substring(0, 8) == "charset=")
      {
        return parts[i].substring(8, parts[i].length);
      }
    }
  }
  catch (e)
  {
  }
  return "UTF-8"; // default
};

/* Async queue globals */
JSONRpcClient.async_requests = [];
JSONRpcClient.async_inflight = {};
JSONRpcClient.async_responses = [];
JSONRpcClient.async_timeout = null;
JSONRpcClient.num_req_active = 0;

JSONRpcClient._async_handler = function ()
{
  var res,
      req;
  JSONRpcClient.async_timeout = null;

  while (JSONRpcClient.async_responses.length > 0)
  {
    res = JSONRpcClient.async_responses.shift();
    if (res.canceled)
    {
      continue;
    }
    if (res.profile)
    {
      res.profile.dispatch = new Date();
    }
    try
    {
      res.cb(res.result, res.ex, res.profile);
    }
    catch(e)
    {
      JSONRpcClient.toplevel_ex_handler(e);
    }
  }

  while (JSONRpcClient.async_requests.length > 0 &&
         JSONRpcClient.num_req_active < JSONRpcClient.max_req_active)
  {
    req = JSONRpcClient.async_requests.shift();
    if (req.canceled)
    {
      continue;
    }
    JSONRpcClient._sendRequest(req.client, req);
  }
};

JSONRpcClient.kick_async = function ()
{
  if (!JSONRpcClient.async_timeout)
  {
    JSONRpcClient.async_timeout = setTimeout(JSONRpcClient._async_handler, 0);
  }
};

JSONRpcClient.cancelRequest = function (requestId)
{
  /* If it is in flight then mark it as canceled in the inflight map
      and the XMLHttpRequest callback will discard the reply. */
  if (JSONRpcClient.async_inflight[requestId])
  {
    JSONRpcClient.async_inflight[requestId].canceled = true;
    return true;
  }
  var i;

  /* If its not in flight yet then we can just mark it as canceled in
      the the request queue and it will get discarded before being sent. */
  for (i in JSONRpcClient.async_requests)
  {
    if (JSONRpcClient.async_requests[i].requestId == requestId)
    {
      JSONRpcClient.async_requests[i].canceled = true;
      return true;
    }
  }

  /* It may have returned from the network and be waiting for its callback
      to be dispatched, so mark it as canceled in the response queue
      and the response will get discarded before calling the callback. */
  for (i in JSONRpcClient.async_responses)
  {
    if (JSONRpcClient.async_responses[i].requestId == requestId)
    {
      JSONRpcClient.async_responses[i].canceled = true;
      return true;
    }
  }

  return false;
};

JSONRpcClient._makeRequest = function (client,methodName, args,objectID,cb, isnotify)
{
  var req = {};
  req.client = client;
  req.requestId = !isnotify ? JSONRpcClient.requestId++ : null;

  var obj = '{"jsonrpc":"2.0", "id":'+req.requestId+',"method":';

  if ((objectID)&&(objectID>0))
  {
    obj += "\".obj[" + objectID + "]." + methodName +"\"";
  }
  else
  {
    obj += "\"" + methodName + "\"";
  }

//TODO: i dont think this if works
  if (cb)
  {
    req.cb = cb;
  }
  if (JSONRpcClient.profile_async)
  {
    req.profile = {submit: new Date() };
  }

  obj += ',"params":' + JSON.stringify(args)+'}';

  req.data = obj;

  return req;
};

JSONRpcClient._sendRequest = function (client,req, isnotify)
{
  var http;
  if (req.profile)
  {
    req.profile.start = new Date();
  }

  /* Get free http object from the pool */
  http = JSONRpcClient.poolGetHTTPRequest();
  JSONRpcClient.num_req_active++;

  /* Send the request */
  var isasync=(!!req.cb) || (!!isnotify);
  //console.log("async post=",isasync, "req.cb", req.cb, "isnotify", isnotify);
  http.open("POST", client.serverURL, isasync, client.user, client.pass);

  /* setRequestHeader is missing in Opera 8 Beta */
  try
  {
    http.setRequestHeader("Content-type", "application/json-rpc");
  }
  catch(e)
  {
  }

  /* Construct call back if we have one */
  if (req.cb)
  {
    http.onreadystatechange = function()
    {
      var res;
      if (http.readyState == 4)
      {
        http.onreadystatechange = function ()
        {
        };
        res = {cb: req.cb, result: null, ex: null};
        if (req.profile)
        {
          res.profile = req.profile;
          res.profile.end = new Date();
        }
        else
        {
          res.profile = false;
        }
        try
        {
          res.result = client._handleResponse(http);
        }
        catch(e)
        {
          res.ex = e;
        }
        if (!JSONRpcClient.async_inflight[req.requestId].canceled)
        {
          JSONRpcClient.async_responses.push(res);
        }
        delete JSONRpcClient.async_inflight[req.requestId];
        JSONRpcClient.kick_async();
      }
    };
  }
  else
  {
    http.onreadystatechange = function()
    {
    };
  }

  if(req.requestId!=null) JSONRpcClient.async_inflight[req.requestId] = req;

  try
  {
    http.send(req.data);
  }
  catch(e)
  {
    JSONRpcClient.poolReturnHTTPRequest(http);
    JSONRpcClient.num_req_active--;
    throw new JSONRpcClient.Exception(
      {
        code: JSONRpcClient.Exception.CODE_ERR_CLIENT,
        message: "Connection failed"
      } );
  }

  if (!req.cb && req.requestId!=null)
  {
    delete JSONRpcClient.async_inflight[req.requestId];
    return client._handleResponse(http);
  }
  return null;
};

JSONRpcClient.prototype._handleResponse = function (http)
{
  /* Get the charset */
  if (!this.charset)
  {
    this.charset = JSONRpcClient._getCharsetFromHeaders(http);
  }

  /* Get request results */
  var status, statusText, data;
  try
  {
    status = http.status;
    statusText = http.statusText;
    data = http.responseText;
  }
  catch(e)
  {
/*
    todo:   don't throw away the original error information here!!
    todo:   and everywhere else, as well!
    if (e instanceof Error)
    {
      alert (e.name + ": " + e.message);
    }
*/
    JSONRpcClient.poolReturnHTTPRequest(http);
    JSONRpcClient.num_req_active--;
    JSONRpcClient.kick_async();
    throw new JSONRpcClient.Exception(
      {
        code: JSONRpcClient.Exception.CODE_ERR_CLIENT,
        message: "Connection failed"
      });
  }

  /* Return http object to the pool; */
  JSONRpcClient.poolReturnHTTPRequest(http);
  JSONRpcClient.num_req_active--;

  /* Unmarshall the response */
  if (status != 200)
  {
    throw new JSONRpcClient.Exception({ code: status, message: statusText });
  };
  return this.unmarshallResponse(data);
};

JSONRpcClient.prototype.unmarshallResponse=function(data)
{
  /**
   * Apply fixups.
   * @param obj root object to apply fixups against.
   * @param fixups array of fixups to apply.  each element of this array is a 2 element array, containing
   *        the array with the fixup location followed by an array with the original location to fix up into the fixup
   *        location.
   */
  function applyFixups(obj, fixups)
  {
    function findOriginal(ob, original)
    {
      for (var i=0,j=original.length;i<j;i++)
      {
        ob = ob[original[i]];
      }
      return ob;
    }
    function applyFixup(ob, fixups, value)
    {
      var j=fixups.length-1;
      for (var i=0;i<j;i++)
      {
        ob = ob[fixups[i]];
      }
      ob[fixups[j]] = value;
    }
    for (var i = 0,j = fixups.length; i < j; i++)
    {
      applyFixup(obj,fixups[i][0],findOriginal(obj,fixups[i][1]));
    }
  }
  /**
   * Traverse the resulting object graph and replace serialized date objects with javascript dates. An object is
   * replaced with a JS date when any of the following conditions is true:
   *   The object has a class hint, and the value of the hint is 'java.util.Date'
   *   The object does not have a class hint, and the ONE AND ONLY property is 'time'
   * Note that the traversal creates an infinite loop if the object graph is not a DAG, so do not call this function
   * after fixing up circular refs.
   * @param obj root of the object graph where dates should be replaces.
   * @return object graph where serialized date objects are replaced by javascript dates.
   */
  function transform_date(obj)
  {
    var hint,foo,num,i,jsDate
    if (obj && typeof obj === 'object')
    {
      hint = obj.hasOwnProperty('javaClass');
      foo = hint ? obj.javaClass === 'java.util.Date' : obj.hasOwnProperty('time');
      num = 0;
      // if there is no class hint but the object has 'time' property, count its properties
      if (!hint && foo)
      {
        for (i in obj)
        {
          if (obj.hasOwnProperty(i))
          {
            num++;
          }
        }
      }
      // if class hint is java.util.Date or no class hint set, but the only property is named 'time', we create jsdate
      if (hint && foo || foo && num === 1)
      {
        jsDate = new Date(obj.time);
        return jsDate;
      }
      else
      {
        for (i in obj)
        {
          if (obj.hasOwnProperty(i))
          {
            obj[i] = transform_date(obj[i]);
          }
        }
        return obj;
      }
    }
    else
    {
      return obj;
    }
  }

  var obj;
  try
  {
	obj=JSON.parse(data);
  }
  catch(e)
  {
    throw new JSONRpcClient.Exception({ code: 550, message: "error parsing result" });
  }
  if (obj.error)
  {
    throw new JSONRpcClient.Exception (obj.error);
  }
  var r = obj.result;

  // look for circular reference/duplicates fixups and execute them
  // if they are there

  var i,tmp;

  /* Handle CallableProxy */
  if (r)
  {
    if(r.objectID && r.JSONRPCType == "CallableReference")
    {
      return this.createCallableProxy(r.objectID,r.javaClass);
    }
    else
    {
      r=JSONRpcClient.extractCallableReferences(this, JSONRpcClient.transformDates ? transform_date(r) : r);
      if (obj.fixups)
      {
        applyFixups(r,obj.fixups);
      }
    }
  }
  return r;
};

JSONRpcClient.extractCallableReferences = function(client,root)
{
  var i,tmp,value;
  for (i in root)
  {
    if(typeof(root[i])=="object")
    {
      tmp=JSONRpcClient.makeCallableReference(client,root[i]);
      if(tmp)
      {
        root[i]=tmp;
      }
      else
      {
        tmp=JSONRpcClient.extractCallableReferences(client,root[i]);
        root[i]=tmp;
      }
    }
    if(typeof(i)=="object")
    {
      tmp=JSONRpcClient.makeCallableReference(client,i);
      if(tmp)
      {
        value=root[i];
        delete root[i];
        root[tmp]=value;
      }
      else
      {
        tmp=JSONRpcClient.extractCallableReferences(client,i);
        value=root[i];
        delete root[i];
        root[tmp]=value;
      }
    }
  }
  return root;
};

JSONRpcClient.makeCallableReference = function(client,value)
{
  if(value && value.objectID && value.javaClass && value.JSONRPCType == "CallableReference")
  {
    return client.createCallableProxy(value.objectID,value.javaClass);
  }
  return null;
};

/* XMLHttpRequest wrapper code */

/* XMLHttpRequest pool globals */
JSONRpcClient.http_spare = [];
JSONRpcClient.http_max_spare = 8;

JSONRpcClient.poolGetHTTPRequest = function ()
{
  // atomic test and fetch spare
  // (pop returns undefined if http_spare is empty)
  var http = JSONRpcClient.http_spare.pop();
  if(http)
  {
    return http;
  }
  return JSONRpcClient.getHTTPRequest();
};

JSONRpcClient.poolReturnHTTPRequest = function (http)
{
  if (JSONRpcClient.http_spare.length >= JSONRpcClient.http_max_spare)
  {
    delete http;
  }
  else
  {
    JSONRpcClient.http_spare.push(http);
  }
};

/* the search order here may seem strange, but it's
   actually what Microsoft recommends */
JSONRpcClient.msxmlNames = [
  "MSXML2.XMLHTTP.6.0",
  "MSXML2.XMLHTTP.3.0",
  "MSXML2.XMLHTTP",
  "MSXML2.XMLHTTP.5.0",
  "MSXML2.XMLHTTP.4.0",
  "Microsoft.XMLHTTP" ];

JSONRpcClient.getHTTPRequest = function ()
{
  /* Look for a browser native XMLHttpRequest implementation (Mozilla/IE7/Opera/Safari, etc.) */
  try
  {
    JSONRpcClient.httpObjectName = "XMLHttpRequest";
    return new XMLHttpRequest();
  }
  catch(e)
  {
  }

  /* Microsoft MSXML ActiveX for IE versions < 7 */
  for (var i = 0; i < JSONRpcClient.msxmlNames.length; i++)
  {
    try
    {
      JSONRpcClient.httpObjectName = JSONRpcClient.msxmlNames[i];
      return new ActiveXObject(JSONRpcClient.msxmlNames[i]);
    }
    catch (e)
    {
    }
  }

  /* None found */
  JSONRpcClient.httpObjectName = null;
  throw new JSONRpcClient.Exception(
    {
      code: 0,
      message: "Can't create XMLHttpRequest object"
    });
};

