use gst::glib;
use gst::prelude::*;

mod imp;

glib::wrapper! {
    pub struct GlFeedback(ObjectSubclass<imp::GlFeedback>)
        @extends gst_gl::GLFilter, gst_gl::GLBaseFilter,
                 gst_base::BaseTransform, gst::Element, gst::Object;
}

pub fn register(plugin: &gst::Plugin) -> Result<(), glib::BoolError> {
    gst::Element::register(
        Some(plugin),
        "glfeedback",
        gst::Rank::NONE,
        GlFeedback::static_type(),
    )
}
