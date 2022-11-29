#!/usr/bin/env python
# -*- coding: utf-8
# Create a fake video that can test synchronization features

import sys, os, time, re
import cairo
import gc
from contextlib import contextmanager

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

from gi.repository import Pango
from gi.repository import PangoCairo

from gi.repository import Rsvg


Gst.init(None)

class GstRenderer :
    def __init__(self, outfile, width, height) :
        self.width = width
        self.height = height
        
        self.src_v = Gst.ElementFactory.make("appsrc", "vidsrc")
        vcvt = Gst.ElementFactory.make("videoconvert", "vidcvt")
        venc = Gst.ElementFactory.make("avenc_mpeg2video", "videnc")
        venc.set_property("bitrate", 2000000)

        mp4mux = Gst.ElementFactory.make("mpegtsmux", "mux")
        filesink = Gst.ElementFactory.make("filesink", "sink")
        filesink.set_property("location", outfile)


        self.pipeline = Gst.Pipeline()
        self.pipeline.add(self.src_v)
        self.pipeline.add(vcvt)
        self.pipeline.add(venc)
        self.pipeline.add(mp4mux)
        self.pipeline.add(filesink)

        caps = Gst.Caps.from_string(f"video/x-raw,format=(string)BGRx,width={width},height={height},framerate=25/1")
        assert(caps is not None)
        self.src_v.set_property("caps", caps)
        self.src_v.set_property("format", Gst.Format.TIME)

        self.src_v.link(vcvt)
        vcvt.link_filtered(venc, Gst.Caps.from_string("video/x-raw,format=(string)I420"))
        venc.link(mp4mux)

        mp4mux.link(filesink)


        self.pipeline.set_state(Gst.State.PLAYING)

    def make_buffer(self) :
        return Gst.Buffer.new_allocate(None, self.width*self.height*4, None)
        
    @contextmanager
    def buffer_to_surface(self, buf) :
        mem = buf.map(Gst.MapFlags.READ | Gst.MapFlags.WRITE)
        surf = cairo.ImageSurface.create_for_data(mem.data, cairo.Format.RGB24, self.width, self.height)
        try :
            yield surf
        finally :
            surf.finish()
            surf.flush()
            del surf
            buf.unmap(mem)

    
    def push_buffer(self, buf) :
        self.src_v.emit("push-buffer", buf)

    def finish(self) :
        self.src_v.emit("end-of-stream")

        bus = self.pipeline.get_bus()
        while True:
            msg = bus.poll(Gst.MessageType.ANY, Gst.CLOCK_TIME_NONE)
            t = msg.type
            if t == Gst.MessageType.EOS:
                print("EOS")
                self.pipeline.set_state(Gst.State.NULL)
                break
                
            elif t == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print("Error: %s" % err, debug)
                break
            elif t == Gst.MessageType.WARNING:
                err, debug = msg.parse_warning()
                print("Warning: %s" % err, debug)
            elif t == Gst.MessageType.STATE_CHANGED:
                pass
            elif t == Gst.MessageType.STREAM_STATUS:
                pass
            else:
                print(t)
                #pipeline.recalculate_latency()
                print("Unknown message: %s" % msg)
        self.pipeline.set_state(Gst.State.NULL)
