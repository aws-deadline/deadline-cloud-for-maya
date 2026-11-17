/* Temporary native graphics diagnostics for the Linux CI bring-up. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <GL/glx.h>

XVisualInfo *glXChooseVisual(Display *display, int screen, int *attributes) {
    XVisualInfo *(*next)(Display *, int, int *) = dlsym(RTLD_NEXT, "glXChooseVisual");
    XVisualInfo *result = next(display, screen, attributes);
    fprintf(stderr, "MAYA_GLX choose display=%p screen=%d visual=%p attrs:",
            (void *)display, screen, (void *)result);
    for (int i = 0; i < 40 && attributes[i]; i++) {
        fprintf(stderr, " %d", attributes[i]);
    }
    fprintf(stderr, "\n");
    return result;
}

GLXContext glXCreateContext(Display *display, XVisualInfo *visual,
                           GLXContext share, Bool direct) {
    GLXContext (*next)(Display *, XVisualInfo *, GLXContext, Bool) =
        dlsym(RTLD_NEXT, "glXCreateContext");
    fprintf(stderr, "MAYA_GLX create display=%p visual=%p share=%p direct=%d\n",
            (void *)display, (void *)visual, (void *)share, direct);
    fflush(stderr);
    GLXContext result = next(display, visual, share, direct);
    fprintf(stderr, "MAYA_GLX created=%p\n", (void *)result);
    return result;
}
