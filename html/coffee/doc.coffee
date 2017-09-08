class cldoc.Doc extends cldoc.Node
    @magic_separator = '%~@@~%'

    @init: ->
        origproto = marked.InlineLexer.prototype.outputLink

        marked.InlineLexer.prototype.outputLink = (cap, link) ->
            orighref = link.href

            if link.href.match(/^[a-z]+:/) == null && link.href[0] != '/'
                link.href = cldoc.host + '/' + link.href

            ret = origproto.call(this, cap, link)
            link.href = orighref

            return ret

    constructor: (@node) ->
        super(@node)

    @either: (node) ->
        brief = @brief(node)
        doc = @doc(node)

        ret = ''

        if brief
            ret += brief

        if doc
            ret += doc

        return ret

    @brief: (node) ->
        return new Doc(node.children('brief')).render()

    @doc: (node) ->
        return new Doc(node.children('doc')).render()

    escape: (text) ->
        r = /([*_\\`{}#+-.!\[\]])/g

        return text.replace(r, (m) -> "\\" + m)

    unescape: (text) ->
        return text.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")

    process_markdown: (text) ->
        rend = new marked.Renderer()

        marked_options =
            highlight: (code) ->
                return hljs.highlightAuto(code).value
            renderer: rend

        marked.setOptions(marked_options)

        html = marked(@unescape(@unescape(text)))

        parts = html.split(Doc.magic_separator)
        rethtml = ''

        for i in [0..parts.length-2] by 3
            a = cldoc.Page.make_link(parts[i + 1], parts[i + 2])
            rethtml += parts[i] + a

        return rethtml + parts[parts.length - 1]

    process_code: (code) ->
        ret = '<pre><code>'
        e = cldoc.html_escape

        for c in $(code).contents()
            if c.nodeType == document.ELEMENT_NODE
                tag = c.tagName.toLowerCase()

                c = $(c)

                if tag == 'ref'
                    ret += cldoc.Page.make_link(c.attr('ref'), c.attr('name'))
                else
                    ret += '<span class="' + e(tag) + '">' + e(c.text()) + '</span>'
            else
                ret += e($(c).text())

        return ret + '</code></pre>'

    render: ->
        if !@node
            return ''

        e = cldoc.html_escape
        ret = '<div class="' + e(cldoc.tag(@node)[0]) + '">'

        contents = @node.contents()
        astext = ''

        msep = Doc.magic_separator

        for c in contents
            if c.nodeType == document.ELEMENT_NODE
                tag = c.tagName.toLowerCase()

                if tag == 'ref'
                    # Add markdown link
                    c = $(c)
                    astext += '<code>' + @escape(msep + c.attr('ref') + msep + c.text() + msep) + '</code>'
                else if tag == 'code'
                    # Do the code!
                    if astext
                        ret += @process_markdown(astext)
                        astext = ''

                    ret += @process_code(c)
            else
                astext += $(c).text()

        if astext
            ret += @process_markdown(astext)

        return ret + '</div>'

cldoc.Node.types.doc = cldoc.Doc

# vi:ts=4:et
