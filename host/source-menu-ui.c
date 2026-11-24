// SDL2 source selector renderer. Text/coordinates are baked into the BMP;
// stdin receives button names on press and "none" on release.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>

typedef struct SDL_Window SDL_Window;
typedef struct SDL_Renderer SDL_Renderer;
typedef struct SDL_Texture SDL_Texture;
typedef struct SDL_Surface SDL_Surface;
typedef struct SDL_RWops SDL_RWops;
typedef struct { int x, y, w, h; } SDL_Rect;
extern int SDL_Init(unsigned int);
extern void SDL_Quit(void);
extern const char *SDL_GetError(void);
extern SDL_Window *SDL_CreateWindow(const char *,int,int,int,int,unsigned int);
extern void SDL_DestroyWindow(SDL_Window *);
extern SDL_Renderer *SDL_CreateRenderer(SDL_Window *,int,unsigned int);
extern void SDL_DestroyRenderer(SDL_Renderer *);
extern int SDL_RenderSetLogicalSize(SDL_Renderer *,int,int);
extern SDL_RWops *SDL_RWFromFile(const char *,const char *);
extern SDL_Surface *SDL_LoadBMP_RW(SDL_RWops *,int);
extern void SDL_FreeSurface(SDL_Surface *);
extern SDL_Texture *SDL_CreateTextureFromSurface(SDL_Renderer *,SDL_Surface *);
extern void SDL_DestroyTexture(SDL_Texture *);
extern int SDL_RenderCopy(SDL_Renderer *,SDL_Texture *,const SDL_Rect *,const SDL_Rect *);
extern int SDL_SetRenderDrawBlendMode(SDL_Renderer *,int);
extern int SDL_SetRenderDrawColor(SDL_Renderer *,unsigned char,unsigned char,unsigned char,unsigned char);
extern int SDL_RenderFillRect(SDL_Renderer *,const SDL_Rect *);
extern void SDL_RenderPresent(SDL_Renderer *);
extern int SDL_PollEvent(void *);

static void paint(SDL_Renderer *renderer, SDL_Texture *texture, const char *pressed) {
    static const char *names[]={"fm","am","cd","aux","external","back"};
    SDL_RenderCopy(renderer,texture,NULL,NULL);
    for(int i=0;i<6;i++) {
        if(strcmp(pressed,names[i])) continue;
        SDL_Rect r;
        if(i==5) r=(SDL_Rect){353,8,114,27};
        else r=(SDL_Rect){11+(i%3)*156,48+(i/3)*56,141,42};
        SDL_SetRenderDrawBlendMode(renderer,1); // SDL_BLENDMODE_BLEND
        SDL_SetRenderDrawColor(renderer,255,166,25,110);
        SDL_RenderFillRect(renderer,&r);
        break;
    }
    SDL_RenderPresent(renderer);
}

int main(int argc,char **argv) {
    if(argc!=2 || SDL_Init(0x20)!=0) { fprintf(stderr,"SDL init: %s\n",SDL_GetError()); return 1; }
    SDL_Window *w=SDL_CreateWindow("Источник",0,0,480,234,0x1015);
    if(!w) { fprintf(stderr,"SDL window: %s\n",SDL_GetError()); SDL_Quit(); return 1; }
    SDL_Renderer *r=SDL_CreateRenderer(w,-1,2);
    if(!r) r=SDL_CreateRenderer(w,-1,1);
    SDL_RWops *rw=SDL_RWFromFile(argv[1],"rb");
    SDL_Surface *surface=rw?SDL_LoadBMP_RW(rw,1):NULL;
    SDL_Texture *texture=(r && surface)?SDL_CreateTextureFromSurface(r,surface):NULL;
    if(surface) SDL_FreeSurface(surface);
    if(!texture) { fprintf(stderr,"SDL renderer/BMP: %s\n",SDL_GetError()); if(r)SDL_DestroyRenderer(r); SDL_DestroyWindow(w); SDL_Quit(); return 1; }
    SDL_RenderSetLogicalSize(r,480,234);
    paint(r,texture,"none");
    fprintf(stderr,"SOURCE_MENU_UI_READY\n");
    char line[64]; size_t used=0; unsigned char event[128];
    for(;;) {
        while(SDL_PollEvent(event)) {}
        fd_set fds; FD_ZERO(&fds); FD_SET(STDIN_FILENO,&fds);
        struct timeval tv={0,100000};
        int ready=select(STDIN_FILENO+1,&fds,NULL,NULL,&tv);
        if(ready<0) break;
        if(ready>0) {
            char buf[128]; ssize_t n=read(STDIN_FILENO,buf,sizeof(buf));
            if(n<=0) break;
            for(ssize_t i=0;i<n;i++) {
                if(buf[i]=='\n') { line[used]='\0'; paint(r,texture,line); used=0; }
                else if(used<sizeof(line)-1) line[used++]=buf[i];
            }
        }
    }
    SDL_DestroyTexture(texture); SDL_DestroyRenderer(r); SDL_DestroyWindow(w); SDL_Quit();
    return 0;
}
