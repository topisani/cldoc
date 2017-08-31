# This file is part of cldoc.  cldoc is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from __future__ import absolute_import
from cldoc.clang import cindex

from .generator import Generator
from cldoc import nodes
from cldoc import example
from cldoc import utf8

from xml.etree import ElementTree
import sys, os

from cldoc import fs

class Xml(Generator):
    def generate(self, outdir):
        if not outdir:
            outdir = 'xml'

        try:
            fs.fs.makedirs(outdir)
        except OSError:
            pass

        ElementTree.register_namespace('gobject', 'http://jessevdk.github.com/cldoc/gobject/1.0')
        ElementTree.register_namespace('cldoc', 'http://jessevdk.github.com/cldoc/1.0')

        self.index = ElementTree.Element('index')
        self.written = {}

        self.indexmap = {
            self.tree.root: self.index
        }

        cm = self.tree.root.comment

        if cm:
            if cm.brief:
                self.index.append(self.doc_to_xml(self.tree.root, cm.brief, 'brief'))

            if cm.doc:
                self.index.append(self.doc_to_xml(self.tree.root, cm.doc))

        Generator.generate(self, outdir)

        if self.options.report:
            self.add_report()

        self.write_xml(self.index, 'index.xml')

        print('Generated `{0}\''.format(outdir))

    def add_report(self):
        from .report import Report

        reportname = 'report'

        while reportname + '.xml' in self.written:
            reportname = '_' + reportname

        page = Report(self.tree, self.options).generate(reportname)

        elem = ElementTree.Element('report')
        elem.set('name', 'Documentation generator')
        elem.set('ref', reportname)

        self.index.append(elem)

        self.write_xml(page, reportname + '.xml')

    def indent(self, elem, level=0):
        i = "\n" + "  " * level

        if elem.tag == 'doc':
            return

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "

            for e in elem:
                self.indent(e, level + 1)

                if not e.tail or not e.tail.strip():
                    e.tail = i + "  "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def write_xml(self, elem, fname):
        self.written[fname] = True

        elem.attrib['xmlns'] = 'http://jessevdk.github.com/cldoc/1.0'

        tree = ElementTree.ElementTree(elem)

        self.indent(tree.getroot())

        f = fs.fs.open(os.path.join(self.outdir, fname), 'w')
        tree.write(f, encoding='utf-8', xml_declaration=True)
        f.write('\n')

        f.close()

    def is_page(self, node):
        if node.force_page:
            return True

        if isinstance(node, nodes.Struct) and node.is_anonymous:
            return False

        if isinstance(node, nodes.Class):
            for child in node.children:
                if not (isinstance(child, nodes.Field) or \
                        isinstance(child, nodes.Variable) or \
                        isinstance(child, nodes.TemplateTypeParameter)):
                    return True

            return False

        pagecls = [nodes.Namespace, nodes.Category, nodes.Root]

        for cls in pagecls:
            if isinstance(node, cls):
                return True

        if isinstance(node, nodes.Typedef) and len(node.children) > 0:
            return True

        return False

    def is_top(self, node):
        if self.is_page(node):
            return True

        if node.parent == self.tree.root:
            return True

        return False

    def refid(self, node):
        if not node._refid is None:
            return node._refid

        parent = node

        meid = node.qid

        if not node.parent or (isinstance(node.parent, nodes.Root) and not self.is_page(node)):
            return 'index#' + meid

        # Find topmost parent
        while not self.is_page(parent):
            parent = parent.parent

        if not node is None:
            node._refid = parent.qid + '#' + meid
            return node._refid
        else:
            return None

    def add_ref_node_id(self, node, elem):
        r = self.refid(node)

        if not r is None:
            elem.set('ref', r)

    def add_ref_id(self, cursor, elem):
        if not cursor:
            return

        if cursor in self.tree.cursor_to_node:
            node = self.tree.cursor_to_node[cursor]
        elif cursor.get_usr() in self.tree.usr_to_node:
            node = self.tree.usr_to_node[cursor.get_usr()]
        else:
            return

        self.add_ref_node_id(node, elem)

    def type_to_xml(self, tp, parent=None):
        elem = ElementTree.Element('type')

        if tp.is_constant_array:
            elem.set('size', str(tp.constant_array_size))
            elem.set('class', 'array')
            elem.append(self.type_to_xml(tp.element_type, parent))
        elif tp.is_function:
            elem.set('class', 'function')

            result = ElementTree.Element('result')
            result.append(self.type_to_xml(tp.function_result, parent))
            elem.append(result)

            args = ElementTree.Element('arguments')
            elem.append(args)

            for arg in tp.function_arguments:
                args.append(self.type_to_xml(arg, parent))
        else:
            elem.set('name', tp.typename_for(parent))

        if len(tp.qualifier) > 0:
            elem.set('qualifier', tp.qualifier_string)

        if tp.builtin:
            elem.set('builtin', 'yes')

        if tp.is_out:
            elem.set('out', 'yes')

        if tp.transfer_ownership != 'none':
            elem.set('transfer-ownership', tp.transfer_ownership)

        if tp.allow_none:
            elem.set('allow-none', 'yes')

        self.add_ref_id(tp.decl, elem)
        return elem

    def enumvalue_to_xml(self, node, elem):
        elem.set('value', str(node.value))

    def enum_to_xml(self, node, elem):
        if not node.typedef is None:
            elem.set('typedef', 'yes')

        if node.isclass:
            elem.set('class', 'yes')

    def struct_to_xml(self, node, elem):
        self.class_to_xml(node, elem)

        if not node.typedef is None:
            elem.set('typedef', 'yes')

    def templatetypeparameter_to_xml(self, node, elem):
        dt = node.default_type

        if not dt is None:
            d = ElementTree.Element('default')

            d.append(self.type_to_xml(dt))
            elem.append(d)

    def templatenontypeparameter_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type))

    def function_to_xml(self, node, elem):
        if not (isinstance(node, nodes.Constructor) or
                isinstance(node, nodes.Destructor)):
            ret = ElementTree.Element('return')

            if not node.comment is None and hasattr(node.comment, 'returns') and node.comment.returns:
                ret.append(self.doc_to_xml(node, node.comment.returns))

            elem.append(ElementTree.Element("undocumented-return"))

            tp = self.type_to_xml(node.return_type, node.parent)

            ret.append(tp)
            elem.append(ret)

        for arg in node.arguments:
            ret = ElementTree.Element('argument')
            ret.set('name', arg.name)
            ret.set('id', arg.qid)

            if not node.comment is None and arg.name in node.comment.params:
                ret.append(self.doc_to_xml(node, node.comment.params[arg.name]))

            ret.append(self.type_to_xml(arg.type, node.parent))
            elem.append(ret)

    def method_to_xml(self, node, elem):
        self.function_to_xml(node, elem)

        if len(node.override) > 0:
            elem.set('override', 'yes')

        for ov in node.override:
            ovelem = ElementTree.Element('override')

            ovelem.set('name', ov.qid_to(node.qid))
            self.add_ref_node_id(ov, ovelem)

            elem.append(ovelem)

        if node.virtual:
            elem.set('virtual', 'yes')

        if node.static:
            elem.set('static', 'yes')

        if node.abstract:
            elem.set('abstract', 'yes')

    def typedef_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node))

    def typedef_to_xml_ref(self, node, elem):
        elem.append(self.type_to_xml(node.type, node))

    def variable_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def property_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def set_access_attribute(self, node, elem):
        if node.access == cindex.AccessSpecifier.PROTECTED:
            elem.set('access', 'protected')
        elif node.access == cindex.AccessSpecifier.PRIVATE:
            elem.set('access', 'private')
        elif node.access == cindex.AccessSpecifier.PUBLIC:
            elem.set('access', 'public')

    def process_bases(self, node, elem, bases, tagname):
        for base in bases:
            child = ElementTree.Element(tagname)

            self.set_access_attribute(base, child)

            child.append(self.type_to_xml(base.type, node))

            if base.node and not base.node.comment is None and base.node.comment.brief:
                child.append(self.doc_to_xml(base.node, base.node.comment.brief, 'brief'))

            elem.append(child)

    def process_subclasses(self, node, elem, subclasses, tagname):
        for subcls in subclasses:
            child = ElementTree.Element(tagname)

            self.set_access_attribute(subcls, child)
            self.add_ref_node_id(subcls, child)

            child.set('name', subcls.qid_to(node.qid))

            if not subcls.comment is None and subcls.comment.brief:
                child.append(self.doc_to_xml(subcls, subcls.comment.brief, 'brief'))

            elem.append(child)

    def class_to_xml(self, node, elem):
        self.process_bases(node, elem, node.bases, 'base')
        self.process_bases(node, elem, node.implements, 'implements')

        self.process_subclasses(node, elem, node.subclasses, 'subclass')
        self.process_subclasses(node, elem, node.implemented_by, 'implementedby')

        hasabstract = False
        allabstract = True

        for method in node.methods:
            if method.abstract:
                hasabstract = True
            else:
                allabstract = False

        if hasabstract:
            if allabstract:
                elem.set('interface', 'true')
            else:
                elem.set('abstract', 'true')

    def field_to_xml(self, node, elem):
        elem.append(self.type_to_xml(node.type, node.parent))

    def doc_to_xml(self, parent, doc, tagname='doc'):
        doce = ElementTree.Element(tagname)

        s = ''
        last = None

        for component in doc.components:
            if isinstance(component, utf8.string):
                s += component
            elif isinstance(component, example.Example):
                # Make highlighting
                if last is None:
                    doce.text = s
                else:
                    last.tail = s

                s = ''

                code = ElementTree.Element('code')
                doce.append(code)

                last = code

                for item in component:
                    if item.classes is None:
                        s += item.text
                    else:
                        last.tail = s

                        s = ''
                        par = code

                        for cls in item.classes:
                            e = ElementTree.Element(cls)

                            par.append(e)
                            par = e

                        par.text = item.text
                        last = par

                if last == code:
                    last.text = s
                else:
                    last.tail = s

                s = ''
                last = code
            else:
                if last is None:
                    doce.text = s
                else:
                    last.tail = s

                s = ''

                nds = component[0]
                refname = component[1]

                # Make multiple refs
                for ci in range(len(nds)):
                    cc = nds[ci]

                    last = ElementTree.Element('ref')

                    if refname:
                        last.text = refname
                    else:
                        last.text = parent.qlbl_from(cc)

                    self.add_ref_node_id(cc, last)

                    if ci != len(nds) - 1:
                        if ci == len(nds) - 2:
                            last.tail = ' and '
                        else:
                            last.tail = ', '

                    doce.append(last)

        if last is None:
            doce.text = s
        else:
            last.tail = s

        return doce

    def call_type_specific(self, node, elem, fn):
        clss = [node.__class__]

        while len(clss) > 0:
            cls = clss[0]
            clss = clss[1:]

            if cls == nodes.Node:
                continue

            nm = cls.__name__.lower() + '_' + fn

            if hasattr(self, nm):
                getattr(self, nm)(node, elem)
                break

            if cls != nodes.Node:
                clss.extend(cls.__bases__)

    def node_to_xml(self, node):
        elem = ElementTree.Element(node.classname)
        props = node.props

        for prop in props:
            if props[prop]:
                elem.set(prop, props[prop])

        if not node.comment is None and node.comment.brief:
            elem.append(self.doc_to_xml(node, node.comment.brief, 'brief'))

        if not node.comment is None and node.comment.doc:
            elem.append(self.doc_to_xml(node, node.comment.doc))

        self.call_type_specific(node, elem, 'to_xml')

        for child in node.sorted_children():
            if child.access == cindex.AccessSpecifier.PRIVATE:
                continue

            self.refid(child)

            if self.is_page(child):
                chelem = self.node_to_xml_ref(child)
            else:
                chelem = self.node_to_xml(child)

            elem.append(chelem)

        return elem

    def templated_to_xml_ref(self, node, element):
        for child in node.sorted_children():
            if not (isinstance(child, nodes.TemplateTypeParameter) or isinstance(child, nodes.TemplateNonTypeParameter)):
                continue

            element.append(self.node_to_xml(child))

    def generate_page(self, node):
        elem = self.node_to_xml(node)
        self.write_xml(elem, node.qid.replace('::', '.') + '.xml')

    def node_to_xml_ref(self, node):
        elem = ElementTree.Element(node.classname)
        props = node.props

        # Add reference item to index
        self.add_ref_node_id(node, elem)

        if 'name' in props:
            elem.set('name', props['name'])

        if not node.comment is None and node.comment.brief:
            elem.append(self.doc_to_xml(node, node.comment.brief, 'brief'))

        self.call_type_specific(node, elem, 'to_xml_ref')

        return elem

    def generate_node(self, node):
        # Ignore private stuff
        if node.access == cindex.AccessSpecifier.PRIVATE:
            return

        self.refid(node)

        if self.is_page(node):
            elem = self.node_to_xml_ref(node)

            self.indexmap[node.parent].append(elem)
            self.indexmap[node] = elem

            self.generate_page(node)
        elif self.is_top(node):
            self.index.append(self.node_to_xml(node))

        if isinstance(node, nodes.Namespace) or isinstance(node, nodes.Category):
            # Go deep for namespaces and categories
            Generator.generate_node(self, node)
        elif isinstance(node, nodes.Class):
            # Go deep, but only for inner classes
            Generator.generate_node(self, node, lambda x: isinstance(x, nodes.Class))

# vi:ts=4:et
