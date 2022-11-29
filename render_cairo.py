import gi
gi.require_version('Rsvg', '2.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('Pango', '1.0')
from gi.repository import Pango
from gi.repository import PangoCairo
from gi.repository import Rsvg
import cairo

from svgtemplate import SVGTemplate
from renderlib import Rendertask
import render_gst


import gpn20



task = Rendertask(
            infile = 'intro.svg',
            workdir = 'gpn20/artwork',
            outfile = "intro.ts",
            sequence = gpn20.introFrames,
            parameters = {
                '$title': "Long Long Long title is LONG   ",
                '$persons': 'Long Name of Dr. Dr. Prof. Dr. Long Long'
                }
            )

class TextField :
    def __init__(self, element, font) :
        self.element = element
        self.font = font

textfieldss = {
    "$title": TextField("#title-rect", "Ubuntu 60"),
    "$persons": TextField("#persons-rect", "Ubuntu 40"),
}

def render_to_surface(surf, task, frame, textfields) :
    with SVGTemplate(task, None) as svg :
        svg.replacetext()
        svg.transform(frame)
        svgstr = svg.svgstr
    ctx = cairo.Context(surf)
    rect = Rsvg.Rectangle()
    rect.width = surf.get_width()
    rect.height = surf.get_height()
    handle  = Rsvg.Handle.new_from_data(svgstr.encode())
    handle.render_document(ctx, rect)
    
    for param, value in task.parameters.items() :
        field = textfields[param]
        
        ctx.save()

        rc, ink, log = handle.get_geometry_for_layer(field.element, rect)

        layout = PangoCairo.create_layout(ctx)

        opts = cairo.FontOptions()
        opts.set_antialias(cairo.ANTIALIAS_GRAY)
        PangoCairo.context_set_font_options(layout.get_context(), opts)

        ctx.save()
        font = Pango.FontDescription(field.font)
        layout.set_font_description(font)
        layout.set_text(value)
        layout.set_width(ink.width*Pango.SCALE)

        ctx.translate(ink.x, ink.y)

        
        style = next((x for x in frame if x[0] == param), None)
        opacity = 1
        if style is not None and style[1:3] == ("style", "opacity") :
            opacity = style[3]
        ctx.set_source_rgba(1,1,1, opacity)
        ctx.rectangle(0,0,ink.width,ink.height)
        ctx.clip()
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()
    #del ctx


def render_frames(task, width, height, textfields) :
    gst_renderer = render_gst.GstRenderer(task.outfile, width, height)
    for frame in task.sequence(task.parameters) :
        buf = gst_renderer.make_buffer()
        with gst_renderer.buffer_to_surface(buf) as surf :
            render_to_surface(surf, task, frame, textfields)
            del surf
        gst_renderer.push_buffer(buf)
    gst_renderer.finish()

render_frames(task, 1920, 1080, textfieldss)


