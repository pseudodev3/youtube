#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

struct Color { int r, g, b, a = 255; };
struct Point { double x, y; };
struct Poly { Color c; std::vector<Point> pts; };

static uint64_t fnv1a(const std::string& s) {
    uint64_t h = 1469598103934665603ULL;
    for (unsigned char ch : s) { h ^= ch; h *= 1099511628211ULL; }
    return h;
}

static std::string rgb(const Color& c, bool alpha = false) {
    std::ostringstream o;
    o << c.r << ',' << c.g << ',' << c.b;
    if (alpha) o << ',' << c.a;
    return o.str();
}

static void emit_poly(const Poly& p) {
    std::cout << "P|" << rgb(p.c, true) << '|';
    for (size_t i = 0; i < p.pts.size(); ++i) {
        if (i) std::cout << ';';
        std::cout << std::fixed << std::setprecision(1) << p.pts[i].x << ',' << p.pts[i].y;
    }
    std::cout << '\n';
}

static Poly rect(double x0, double y0, double x1, double y1, Color c) {
    return {c, {{x0,y0},{x1,y0},{x1,y1},{x0,y1}}};
}

static Poly triangle(double cx, double top, double halfw, double bottom, Color c) {
    return {c, {{cx,top},{cx-halfw,bottom},{cx+halfw,bottom}}};
}

static Poly rolling(double width, double base, double amp, double waves, double phase, Color c) {
    Poly p{c,{}};
    p.pts.push_back({0, 900});
    const int n = 24;
    for (int i = 0; i <= n; ++i) {
        double x = width * i / n;
        double y = base + std::sin((i / double(n)) * waves * 2.0 * M_PI + phase) * amp
                         + std::sin((i / double(n)) * (waves * 0.57) * 2.0 * M_PI + phase * 0.63) * amp * 0.34;
        p.pts.push_back({x, y});
    }
    p.pts.push_back({width, 900});
    return p;
}

static Poly peaks(double width, double base, double min_top, double max_top, int count, Color c, std::mt19937_64& rng) {
    Poly p{c,{}};
    p.pts.push_back({0, 900});
    p.pts.push_back({0, base});
    std::uniform_real_distribution<double> top(min_top, max_top);
    for (int i = 0; i < count; ++i) {
        double x0 = width * i / count;
        double x1 = width * (i + 1) / count;
        double cx = (x0 + x1) * 0.5;
        p.pts.push_back({x0, base});
        p.pts.push_back({cx, top(rng)});
        p.pts.push_back({x1, base});
    }
    p.pts.push_back({width, 900});
    return p;
}

static Poly ridge(double width, double base, double min_top, double max_top, int count, Color c, std::mt19937_64& rng) {
    Poly p{c,{}};
    p.pts.push_back({0, 900});
    p.pts.push_back({0, base});
    std::uniform_real_distribution<double> peak(min_top, max_top);
    std::uniform_real_distribution<double> saddle(base-82.0, base-28.0);
    for (int i = 0; i < count; ++i) {
        double x0 = width * i / count;
        double x1 = width * (i + 1) / count;
        double cx = x0 + (x1-x0) * (0.38 + (rng()%25)/100.0);
        p.pts.push_back({x0, saddle(rng)});
        p.pts.push_back({cx, peak(rng)});
        p.pts.push_back({x1, saddle(rng)});
    }
    p.pts.push_back({width, 900});
    return p;
}

struct Style { Color sky0, sky1, ground; };

static Style style_for(const std::string& k) {
    if (k=="training") return {{103,159,205},{199,213,220},{103,108,106}};
    if (k=="country") return {{131,187,224},{224,218,181},{176,151,84}};
    if (k=="mountain") return {{101,139,170},{185,195,199},{70,72,70}};
    if (k=="night_city") return {{12,18,43},{48,52,73},{29,34,43}};
    if (k=="rain") return {{49,66,86},{119,131,139},{53,73,65}};
    if (k=="coast") return {{74,170,228},{215,232,238},{54,139,164}};
    if (k=="snow") return {{156,196,226},{234,242,246},{223,231,234}};
    if (k=="canyon") return {{202,133,91},{240,189,127},{143,82,53}};
    if (k=="desert") return {{226,171,102},{250,216,153},{198,150,83}};
    if (k=="forest") return {{58,106,102},{142,160,137},{40,78,50}};
    if (k=="street") return {{88,110,136},{174,182,190},{70,73,78}};
    if (k=="tunnel") return {{24,27,34},{36,39,46},{40,42,47}};
    if (k=="neon_rain") return {{22,15,49},{70,40,88},{29,32,43}};
    if (k=="alpine") return {{127,176,215},{228,239,244},{188,203,202}};
    if (k=="extreme_canyon") return {{155,71,57},{218,124,80},{112,59,47}};
    return {{91,159,218},{176,211,233},{77,137,72}};
}

static std::vector<Poly> terrain_for(const std::string& k, uint64_t seed, double W=1080.0) {
    std::mt19937_64 rng(seed ^ fnv1a(k));
    std::vector<Poly> out;

    if (k=="training") {
        // Purpose-built test facility: concrete apron, grandstands and timing tower.
        out.push_back(rect(0,585,W,720,{117,121,120,255}));
        out.push_back(rect(35,472,278,604,{69,76,82,250}));
        out.push_back(rect(802,472,1045,604,{69,76,82,250}));
        for (int y=500; y<=580; y+=20) {
            out.push_back(rect(48,y,265,y+5,{201,204,201,205}));
            out.push_back(rect(815,y,1032,y+5,{201,204,201,205}));
        }
        out.push_back(rect(456,430,624,604,{57,63,69,252}));
        out.push_back(rect(484,458,596,520,{151,191,209,225}));
        out.push_back(rect(438,420,642,438,{213,64,55,245}));
        out.push_back(rect(0,601,205,620,{198,201,197,238}));
        out.push_back(rect(875,601,1080,620,{198,201,197,238}));
    } else if (k=="country") {
        // Patchwork farmland: dry crops, hedges and low rolling land rather than a green carpet.
        out.push_back(rolling(W,612,26,2.8,0.3,{129,145,73,255}));
        out.push_back(rolling(W,660,22,2.1,1.0,{194,164,83,255}));
        out.push_back({{219,186,97,248},{{0,630},{260,604},{420,676},{180,720},{0,710}}});
        out.push_back({{151,129,68,248},{{420,622},{690,590},{890,663},{650,718},{430,690}}});
        out.push_back({{204,177,93,248},{{865,610},{1080,585},{1080,720},{910,700}}});
        out.push_back(rect(78,548,190,624,{153,73,48,250}));
        out.push_back({{91,49,38,250},{{62,548},{134,500},{206,548}}});
        out.push_back(rect(216,544,240,624,{188,190,167,245}));
        out.push_back({{203,205,181,245},{{210,544},{228,523},{246,544}}});
        out.push_back(rect(742,565,836,624,{126,83,48,242}));
        out.push_back({{91,58,40,242},{{728,565},{789,528},{850,565}}});
        // Thin distant hedgerow + pale field lane adds depth without turning green again.
        out.push_back(rolling(W,590,9,5.5,0.6,{74,102,52,235}));
        out.push_back(rect(475,585,650,592,{226,211,159,205}));
    } else if (k=="mountain") {
        // Cold layered ridges: broad silhouettes instead of the old saw-tooth triangles.
        out.push_back(ridge(W,690,250,390,5,{70,79,85,230},rng));
        out.push_back(ridge(W,735,335,505,5,{50,57,62,255},rng));
        out.push_back({{43,47,50,255},{{0,455},{112,405},{180,482},{228,603},{170,735},{0,858}}});
        out.push_back({{47,50,53,255},{{1080,438},{968,392},{900,470},{854,598},{910,730},{1080,850}}});
        // Snow streaks sit on only a few summits so the pass stays rocky, not alpine-white.
        out.push_back({{229,235,237,226},{{238,390},{286,292},{330,392},{304,365},{286,330},{267,370}}});
        out.push_back({{235,239,240,218},{{706,374},{766,268},{825,386},{795,350},{765,309},{742,354}}});
        out.push_back({{200,210,213,150},{{490,470},{535,386},{578,474},{553,454},{535,420},{520,455}}});
    } else if (k=="night_city" || k=="neon_rain") {
        Color body = k=="neon_rain" ? Color{15,18,29,255} : Color{20,25,34,255};
        std::uniform_int_distribution<int> hh(120,300);
        int x=0, i=0;
        while (x < 1080) {
            int w = 58 + int((rng()%38));
            int h = hh(rng);
            out.push_back(rect(x,610-h,x+w,615,body));
            // Window rhythm keeps the skyline readable at Shorts resolution.
            Color warm = k=="neon_rain" ? Color{128,88,189,170} : Color{245,204,104,165};
            Color cool = k=="neon_rain" ? Color{45,224,255,150} : Color{91,164,224,135};
            for (int yy=610-h+24; yy<590; yy+=34) {
                out.push_back(rect(x+10,yy,std::min(x+w-10,x+18),yy+8,((yy/34+i)%2)?warm:cool));
                if (w>72) out.push_back(rect(x+w-24,yy,std::min(x+w-10,x+w-16),yy+8,((yy/34+i)%2)?cool:warm));
            }
            if (k=="neon_rain") {
                Color glow = (i%2) ? Color{45,224,255,220} : Color{255,58,207,220};
                out.push_back(rect(x+8,610-h+13,std::min(x+w-8,x+50),610-h+21,glow));
            }
            x += w + 20 + int(rng()%25); ++i;
        }
    } else if (k=="rain") {
        out.push_back(rolling(W,606,20,5.0,0.8,{49,72,61,255}));
        for (int x=-30; x<1110; x+=70) {
            out.push_back(triangle(x+25,492,48,620,{41,64,53,238}));
        }
    } else if (k=="coast") {
        out.push_back(rect(0,548,1080,760,{40,141,191,255}));
        out.push_back(rect(0,586,1080,592,{201,236,244,92}));
        out.push_back(rect(0,632,1080,637,{201,236,244,66}));
        out.push_back({{102,104,92,255},{{0,640},{150,548},{255,660},{170,820},{0,860}}});
        out.push_back({{94,99,88,255},{{1080,640},{930,548},{820,665},{910,825},{1080,865}}});
        // Far headland makes the horizon feel coastal rather than just blue.
        out.push_back({{85,108,101,190},{{520,570},{610,530},{700,548},{790,570},{790,610},{520,610}}});
        out.push_back({{255,219,111,240},{{850,250},{900,225},{950,250},{960,300},{925,340},{875,340},{840,300}}});
    } else if (k=="snow") {
        out.push_back(peaks(W,700,360,500,7,{196,212,222,255},rng));
        out.push_back(peaks(W,748,510,610,7,{239,245,248,250},rng));
    } else if (k=="canyon" || k=="extreme_canyon") {
        bool ex = k=="extreme_canyon";
        Color left = ex ? Color{88,40,37,255}:Color{132,70,48,255};
        Color right = ex ? Color{78,36,35,255}:Color{113,61,45,255};
        double inset = ex ? 290 : 215;
        out.push_back({left,{{0,135},{inset,225},{inset-65,430},{inset+20,610},{inset-58,860},{0,980}}});
        out.push_back({right,{{1080,125},{1080-inset,215},{1080-inset+65,425},{1080-inset-20,605},{1080-inset+58,855},{1080,985}}});
        // Flat-topped mesas sell canyon scale better than triangular "mountains".
        out.push_back({ex?Color{111,51,42,242}:Color{155,82,51,238},{{275,620},{315,515},{355,476},{430,476},{470,520},{505,620}}});
        out.push_back({ex?Color{101,46,40,240}:Color{143,74,49,235},{{610,620},{650,500},{695,458},{782,458},{825,510},{860,620}}});
        // Horizontal strata on the near walls.
        out.push_back(rect(0,338,inset-38,356,ex?Color{112,50,43,190}:Color{173,96,58,180}));
        out.push_back(rect(0,492,inset-16,507,ex?Color{103,46,41,175}:Color{158,84,54,170}));
        out.push_back(rect(1080-inset+38,326,1080,344,ex?Color{103,46,41,185}:Color{162,88,56,180}));
        out.push_back(rect(1080-inset+18,482,1080,497,ex?Color{96,42,39,170}:Color{150,79,52,170}));
    } else if (k=="desert") {
        out.push_back(rolling(W,650,34,2.0,0.1,{208,159,89,255}));
        out.push_back(rolling(W,708,42,1.65,1.3,{231,184,106,250}));
        out.push_back({{156,104,66,195},{{95,620},{135,540},{185,510},{280,510},{330,555},{360,620}}});
        out.push_back({{145,95,63,185},{{610,625},{650,555},{700,530},{790,530},{830,565},{860,625}}});
        out.push_back({{255,221,104,240},{{828,245},{875,220},{925,238},{952,284},{938,333},{888,352},{840,330},{814,285}}});
    } else if (k=="forest") {
        // Two-depth canopy: misty far pines, then dark close trunks.
        for (int x=-20; x<1120; x+=70) {
            int h = 95 + int(rng()%55);
            out.push_back(triangle(x+30,585-h-70,40,615,{53,93,67,175}));
        }
        for (int x=-35; x<1120; x+=54) {
            int h = 140 + int(rng()%95);
            out.push_back(rect(x+20,610-h,x+30,620,{49,40,32,250}));
            out.push_back(triangle(x+25,610-h-100,48,610-h+45,{24,61,39,255}));
            out.push_back(triangle(x+25,610-h-56,42,610-h+74,{31,76,45,250}));
        }
    } else if (k=="street") {
        for (int side=0; side<2; ++side) {
            int start = side==0 ? 0 : 785;
            for (int i=0;i<4;++i) {
                int x=start+i*74, h=170+(i%3)*72;
                out.push_back(rect(x,610-h,x+64,620,{58,62,70,255}));
            }
        }
    } else if (k=="tunnel") {
        out.push_back({{13,16,21,255},{{0,0},{1080,0},{905,560},{175,560}}});
        out.push_back(rect(0,535,165,1000,{27,30,35,255}));
        out.push_back(rect(915,535,1080,1000,{27,30,35,255}));
    } else if (k=="alpine") {
        out.push_back(peaks(W,720,245,430,7,{123,150,165,255},rng));
        out.push_back(peaks(W,760,390,545,7,{239,246,249,248},rng));
    }
    return out;
}

static void emit_object(int frame, const std::string& kind, double x, double y, double s, int variant) {
    std::cout << "O|" << frame << '|' << kind << '|'
              << std::fixed << std::setprecision(2) << x << '|' << y << '|' << s << '|' << variant << '\n';
}

static void emit_roadside(const std::string& k, uint64_t seed, int frames, double fps) {
    int count = 8;
    double speed = 0.06;
    if (k=="training") { count=11; speed=.064; }
    else if (k=="country") { count=12; speed=.055; }
    else if (k=="mountain" || k=="alpine") { count=12; speed=.070; }
    else if (k=="night_city" || k=="street" || k=="neon_rain") { count=12; speed=.075; }
    else if (k=="rain") { count=10; speed=.070; }
    else if (k=="coast") { count=9; speed=.060; }
    else if (k=="snow") { count=11; speed=.065; }
    else if (k=="canyon" || k=="extreme_canyon") { count=12; speed=.073; }
    else if (k=="desert") { count=8; speed=.050; }
    else if (k=="forest") { count=14; speed=.075; }
    else if (k=="tunnel") { count=13; speed=.082; }

    uint64_t base = seed ^ fnv1a(k);
    for (int frame=0; frame<frames; ++frame) {
        double t = frame / std::max(1.0, fps);
        for (int i=0; i<count; ++i) {
            double p = std::fmod((i / double(count)) + t * speed, 1.0);
            double y = 470.0 + std::pow(p, 1.55) * 1040.0;
            double s = 0.28 + p * 1.15;
            int variant = int((base + uint64_t(i*37) + uint64_t(frame/9)*17) % 5);
            for (int side : {-1,1}) {
                double x = side<0 ? 74.0 + (variant%3)*11.0 : 1080.0 - (74.0 + (variant%3)*11.0);
                std::string kind = "marker";
                if (k=="training") kind = (i%5==0 ? "floodlight" : (i%4==0 ? "signboard" : (i%2==0 ? "barrier" : "bollard")));
                else if (k=="country") kind = (i%6==0 ? "utility_pole" : (i%5==0 ? "haybale" : (i%3==0 ? "hedge" : (i%2==0 ? "fence" : "tree"))));
                else if (k=="mountain") kind = (i%4==0 ? "pine" : (i%4==1 ? "rock" : (i%4==2 ? "guardrail" : "warning")));
                else if (k=="night_city") kind = (i%2 ? "lamp" : "barrier");
                else if (k=="rain") kind = (i%3==0 ? "tree" : "bollard");
                else if (k=="coast") kind = (i%4==0 ? "palm" : "guardrail");
                else if (k=="snow") kind = (i%3==0 ? "pine_snow" : "snowbank");
                else if (k=="canyon") kind = (i%4==0 ? "rock" : (i%4==1 ? "scrub" : "warning"));
                else if (k=="desert") kind = (i%3==0 ? "cactus" : "rock");
                else if (k=="forest") kind = (i%2 ? "pine" : "tree_dark");
                else if (k=="street") kind = (i%3==0 ? "lamp" : "barrier");
                else if (k=="tunnel") kind = (i%2 ? "tunnel_light" : "barrier");
                else if (k=="neon_rain") kind = (i%2 ? "neon" : "lamp");
                else if (k=="alpine") kind = (i%3==0 ? "pine_snow" : "rock");
                else if (k=="extreme_canyon") kind = (i%4==0 ? "warning" : (i%4==1 ? "scrub" : "rock"));
                emit_object(frame, kind, x, y, s, variant);
            }
        }
    }
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "usage: map_engine <track> <seed> <frames> <fps>\n";
        return 2;
    }
    const std::string track = argv[1];
    const uint64_t seed = std::stoull(argv[2]);
    const int frames = std::max(1, std::stoi(argv[3]));
    const double fps = std::max(1.0, std::stod(argv[4]));

    Style st = style_for(track);
    std::cout << "S|" << rgb(st.sky0) << '|' << rgb(st.sky1) << '\n';
    std::cout << "G|" << rgb(st.ground) << '\n';
    for (const auto& p : terrain_for(track, seed)) emit_poly(p);
    emit_roadside(track, seed, frames, fps);
    return 0;
}
