class cldoc.Function extends cldoc.Node
    @title = ['Function', 'Functions']

    constructor: (@node) ->
        super(@node)

    identifier_for_display: ->
        @name

    render_arguments: ->
        args = @node.children('argument')
        ret = '<table class="arguments">'

        # Return type
        retu = @node.children('return')
        returntype = null

        if retu.length > 0
            returntype = new cldoc.Type(retu.children('type'))

        e = cldoc.html_escape

        for i in [0..(args.length - 1)] by 1
            arg = $(args[i])
            argtype = new cldoc.Type(arg.children('type'))

            tmp = ''
            tmp += '<tr id="' + e(arg.attr('id')) + '">'
            tmp += '<td>' + e(arg.attr('name')) + '</td>'
            tmp += '<td>' + cldoc.Doc.either(arg)
            display = cldoc.Doc.either(arg) != ''

            if argtype.allow_none
                tmp += '<span class="annotation">(may be <code>NULL</code>)</span>'
                display = true

            tmp += '</td></tr>'
            if display
                ret += tmp

        if returntype and returntype.node.attr('name') != 'void'
            tmp = ''
            tmp += '<tr class="return">'
            tmp += '<td class="keyword">return</td>'
            tmp += '<td>' + cldoc.Doc.either(retu)
            display = cldoc.Doc.either(retu) != ''

            if returntype.transfer_ownership == 'full'
                tmp += '<span class="annotation">(owned by caller)</span>'
                display = true
            else if returntype.transfer_ownership == 'container'
                tmp += '<span class="annotation">(container owned by caller)</span>'
                display = true

            tmp += '</tr>'

            if display
                ret += tmp

        ret += '</table>'

        return ret

    render: ->
        e = cldoc.html_escape

        ret = '<div class="function">'
        ret += '<div class="declaration" id="' + e(@id) + '">'

        isvirt = @node.attr('virtual')
        isprot = @node.attr('access') == 'protected'
        isstat = @node.attr('static')

        if isvirt || isprot || isstat
            ret += '<ul class="specifiers">'

            if isstat
                ret += '<li class="static">static</li>'

            if isprot
                ret += '<li class="protected">protected</li>'

            if isvirt
                isover = @node.attr('override')

                if isover
                    ret += '<li class="override">override</li>'
                else
                    ret += '<li class="virtual">virtual</li>'

                if @node.attr('abstract')
                    ret += '<li class="abstract">abstract</li>'

            ret += '</ul>'

        # Return type
        retu = @node.children('return')
        returntype = null

        if retu.length > 0
            returntype = new cldoc.Type(retu.children('type'))
            ret += '<div class="return_type">' + returntype.render() + '</div>'

        ret += '<table class="declaration">'
        ret += '<tr><td class="identifier">' + e(@identifier_for_display()) + '</td>'
        ret += '<td class="open_paren">(</td>'

        args = @node.children('argument')

        for i in [0..(args.length - 1)] by 1
            if i != 0
                ret += '</tr><tr><td colspan="2"></td>'

            arg = $(args[i])

            argtype = new cldoc.Type(arg.children('type'))
            ret += '<td class="argument_type">' + argtype.render() + '</td>'

            name = arg.attr('name')

            if i != args.length - 1
                name += ','

            ret += '<td class="argument_name">' + e(name) + '</td>'

        if args.length == 0
            ret += '<td colspan="2"></td>'

        ret += '<td class="close_paren">)</td></tr></table></div>'
        ret += cldoc.Doc.either(@node)

        ret += @render_arguments()

        override = @node.children('override')

        if override.length > 0
            ret += '<div class="overrides"><span class="title">Overrides: </span>'

            for i in [0..override.length-1]
                ov = $(override[i])

                if i != 0
                    if i == override.length - 1
                        ret += ' and '
                    else
                        ret += ', '

                ret += cldoc.Page.make_link(ov.attr('ref'), ov.attr('name'))

            ret += '</div>'

        return ret + '</div>'

cldoc.Node.types.function = cldoc.Function

# vi:ts=4:et
