import type {CSSProperties, ReactNode} from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const COLORS = {
  ink: '#060A18',
  inkSoft: '#0B1230',
  panel: 'rgba(14, 25, 57, 0.82)',
  panelStrong: 'rgba(19, 32, 70, 0.95)',
  border: 'rgba(133, 163, 255, 0.22)',
  text: '#F5F7FF',
  textSoft: '#C8D2FF',
  muted: '#8290B8',
  cyan: '#27D6F5',
  cyanSoft: '#95F3FF',
  violet: '#8B5CF6',
  violetSoft: '#C4B5FD',
  green: '#42D7A3',
  amber: '#FFBE55',
  red: '#FF6B81',
} as const;

const TOTAL_FRAMES = 600;

const clamp = (value: number, min = 0, max = 1) =>
  Math.min(max, Math.max(min, value));

const sceneOpacity = (
  frame: number,
  start: number,
  end: number,
  fadeFrames = 16,
) => {
  const inOpacity = interpolate(frame, [start, start + fadeFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const outOpacity = interpolate(frame, [end - fadeFrames, end], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });

  return Math.min(inOpacity, outOpacity);
};

const entrance = (frame: number, start: number, fps: number, distance = 24) => {
  const progress = spring({
    frame: Math.max(0, frame - start),
    fps,
    config: {
      damping: 200,
      stiffness: 110,
      mass: 0.7,
    },
  });

  return {
    opacity: progress,
    transform: `translateY(${interpolate(progress, [0, 1], [distance, 0])}px)`,
  };
};

const staggeredEntrance = (
  frame: number,
  sceneStart: number,
  delay: number,
  fps: number,
  distance = 18,
) => entrance(frame, sceneStart + delay, fps, distance);

const GlassPanel = ({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) => (
  <div
    style={{
      background: COLORS.panel,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 22,
      boxShadow: '0 20px 70px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255,255,255,0.05)',
      backdropFilter: 'blur(16px)',
      ...style,
    }}
  >
    {children}
  </div>
);

const ShieldMark = ({
  size = 48,
  glow = true,
}: {
  size?: number;
  glow?: boolean;
}) => (
  <svg
    aria-label="SquadOS shield"
    width={size}
    height={size}
    viewBox="0 0 64 70"
    style={{
      display: 'block',
      filter: glow ? `drop-shadow(0 0 16px ${COLORS.cyan})` : undefined,
      overflow: 'visible',
    }}
  >
    <path
      d="M32 3L57 12V31C57 47.5 46.8 60.6 32 67 17.2 60.6 7 47.5 7 31V12L32 3Z"
      fill="rgba(39,214,245,0.14)"
      stroke={COLORS.cyan}
      strokeWidth="3"
    />
    <path
      d="M20 34L28.3 42.3L45.5 23"
      fill="none"
      stroke={COLORS.cyanSoft}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="5"
    />
    <circle cx="32" cy="12" r="2.7" fill={COLORS.violetSoft} />
  </svg>
);

const Dot = ({
  color,
  size = 7,
  style,
}: {
  color: string;
  size?: number;
  style?: CSSProperties;
}) => (
  <span
    style={{
      display: 'inline-block',
      height: size,
      width: size,
      borderRadius: '50%',
      background: color,
      boxShadow: `0 0 ${size * 2}px ${color}`,
      ...style,
    }}
  />
);

const networkNodes = [
  {x: 80, y: 106, color: COLORS.violet},
  {x: 155, y: 173, color: COLORS.cyan},
  {x: 255, y: 85, color: COLORS.green},
  {x: 384, y: 137, color: COLORS.cyan},
  {x: 480, y: 55, color: COLORS.violet},
  {x: 602, y: 128, color: COLORS.green},
  {x: 735, y: 67, color: COLORS.cyan},
  {x: 856, y: 132, color: COLORS.violet},
  {x: 975, y: 82, color: COLORS.green},
  {x: 1114, y: 147, color: COLORS.cyan},
  {x: 1192, y: 86, color: COLORS.violet},
  {x: 74, y: 569, color: COLORS.cyan},
  {x: 182, y: 641, color: COLORS.green},
  {x: 318, y: 577, color: COLORS.violet},
  {x: 442, y: 662, color: COLORS.cyan},
  {x: 618, y: 592, color: COLORS.green},
  {x: 766, y: 662, color: COLORS.violet},
  {x: 916, y: 570, color: COLORS.cyan},
  {x: 1047, y: 638, color: COLORS.green},
  {x: 1179, y: 557, color: COLORS.violet},
];

const networkEdges: Array<[number, number]> = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [4, 5],
  [5, 6],
  [6, 7],
  [7, 8],
  [8, 9],
  [9, 10],
  [11, 12],
  [12, 13],
  [13, 14],
  [14, 15],
  [15, 16],
  [16, 17],
  [17, 18],
  [18, 19],
];

const Background = ({frame}: {frame: number}) => {
  const hazeX = 30 + Math.sin(frame / 80) * 4;
  const hazeY = 20 + Math.cos(frame / 95) * 4;

  return (
    <AbsoluteFill
      style={{
        overflow: 'hidden',
        background: `radial-gradient(circle at ${hazeX}% ${hazeY}%, rgba(72, 60, 169, 0.27), transparent 29%), radial-gradient(circle at 84% 78%, rgba(8, 192, 222, 0.13), transparent 31%), linear-gradient(135deg, ${COLORS.ink} 0%, #0B1030 53%, #091B32 100%)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.18,
          backgroundImage:
            'linear-gradient(rgba(112, 146, 250, 0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(112, 146, 250, 0.18) 1px, transparent 1px)',
          backgroundSize: '56px 56px',
          maskImage: 'linear-gradient(to bottom, transparent, black 18%, black 82%, transparent)',
        }}
      />
      <svg
        viewBox="0 0 1280 720"
        preserveAspectRatio="none"
        style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.46}}
      >
        <defs>
          <linearGradient id="network-line" x1="0" x2="1">
            <stop stopColor={COLORS.cyan} stopOpacity="0.03" />
            <stop offset="0.5" stopColor={COLORS.violet} stopOpacity="0.45" />
            <stop offset="1" stopColor={COLORS.cyan} stopOpacity="0.03" />
          </linearGradient>
        </defs>
        {networkEdges.map(([from, to], index) => {
          const source = networkNodes[from];
          const target = networkNodes[to];
          const shimmer = 0.2 + 0.16 * Math.sin(frame / 20 + index);
          return (
            <line
              key={`${from}-${to}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="url(#network-line)"
              strokeWidth="1.2"
              opacity={shimmer}
            />
          );
        })}
        {networkNodes.map((node, index) => {
          const pulse = 1 + 0.3 * Math.sin(frame / 13 + index * 0.8);
          return (
            <g key={`${node.x}-${node.y}`}>
              <circle
                cx={node.x}
                cy={node.y}
                r={7 * pulse}
                fill={node.color}
                opacity="0.08"
              />
              <circle cx={node.x} cy={node.y} r="3.3" fill={node.color} opacity="0.93" />
            </g>
          );
        })}
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(90deg, rgba(6,10,24,0.55), transparent 28%, transparent 72%, rgba(6,10,24,0.38))',
        }}
      />
    </AbsoluteFill>
  );
};

const TourHeader = ({frame}: {frame: number}) => {
  const progress = clamp(frame / (TOTAL_FRAMES - 1));
  const seconds = Math.floor((frame / 30) % 60)
    .toString()
    .padStart(2, '0');

  return (
    <div
      style={{
        position: 'absolute',
        top: 31,
        left: 58,
        right: 58,
        height: 32,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        color: COLORS.textSoft,
        fontFamily: 'Arial, Helvetica, sans-serif',
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: 1.5,
        zIndex: 20,
      }}
    >
      <ShieldMark size={27} />
      <span style={{color: COLORS.text}}>SQUADOS</span>
      <span style={{color: COLORS.muted, fontWeight: 600}}>PRODUCT TOUR</span>
      <div style={{flex: 1}} />
      <div
        style={{
          width: 186,
          height: 4,
          borderRadius: 99,
          overflow: 'hidden',
          background: 'rgba(171, 192, 255, 0.16)',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progress * 100}%`,
            borderRadius: 99,
            background: `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.violet})`,
            boxShadow: `0 0 12px ${COLORS.cyan}`,
          }}
        />
      </div>
      <span style={{width: 40, color: COLORS.muted}}>00:{seconds}</span>
    </div>
  );
};

const Pill = ({
  children,
  accent = COLORS.cyan,
  style,
}: {
  children: ReactNode;
  accent?: string;
  style?: CSSProperties;
}) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      padding: '10px 15px',
      border: `1px solid ${accent}55`,
      background: `${accent}12`,
      borderRadius: 999,
      color: COLORS.textSoft,
      fontFamily: 'Arial, Helvetica, sans-serif',
      fontSize: 15,
      fontWeight: 700,
      letterSpacing: 0.2,
      ...style,
    }}
  >
    <Dot color={accent} size={6} />
    {children}
  </span>
);

const SceneKicker = ({children}: {children: ReactNode}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      color: COLORS.cyanSoft,
      fontFamily: 'Arial, Helvetica, sans-serif',
      fontSize: 14,
      fontWeight: 800,
      letterSpacing: 2.1,
      textTransform: 'uppercase',
    }}
  >
    <span style={{height: 2, width: 26, background: COLORS.cyan, boxShadow: `0 0 12px ${COLORS.cyan}`}} />
    {children}
  </div>
);

const IntroScene = ({frame, fps}: {frame: number; fps: number}) => {
  const opacity = sceneOpacity(frame, 0, 122, 20);
  const markProgress = spring({
    frame,
    fps,
    config: {damping: 16, stiffness: 110, mass: 0.8},
  });
  const rings = 1 + Math.sin(frame / 16) * 0.03;

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          left: 112,
          top: 150,
          width: 720,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={{...staggeredEntrance(frame, 0, 2, fps), display: 'flex', alignItems: 'center', gap: 16}}>
          <div
            style={{
              display: 'grid',
              placeItems: 'center',
              height: 80,
              width: 80,
              borderRadius: 26,
              transform: `scale(${interpolate(markProgress, [0, 1], [0.65, 1])})`,
              background: 'linear-gradient(145deg, rgba(39,214,245,0.18), rgba(139,92,246,0.22))',
              border: '1px solid rgba(105,234,255,0.4)',
              boxShadow: '0 0 55px rgba(39,214,245,0.2)',
            }}
          >
            <ShieldMark size={49} />
          </div>
          <span style={{fontSize: 25, fontWeight: 800, letterSpacing: 5, color: COLORS.textSoft}}>SQUADOS</span>
        </div>

        <h1
          style={{
            ...staggeredEntrance(frame, 0, 12, fps, 30),
            margin: '27px 0 18px',
            fontSize: 72,
            lineHeight: 1.02,
            letterSpacing: -3.7,
            color: COLORS.text,
            fontWeight: 800,
          }}
        >
          The OS for{' '}
          <span
            style={{
              color: COLORS.cyanSoft,
              textShadow: `0 0 30px rgba(39,214,245,0.35)`,
            }}
          >
            AI agent squads.
          </span>
        </h1>
        <p
          style={{
            ...staggeredEntrance(frame, 0, 23, fps),
            margin: 0,
            width: 610,
            color: COLORS.textSoft,
            fontSize: 25,
            lineHeight: 1.4,
            fontWeight: 500,
          }}
        >
          Turn ambitious goals into coordinated, verified work — without losing the human in the loop.
        </p>

        <div
          style={{
            ...staggeredEntrance(frame, 0, 34, fps),
            display: 'flex',
            flexWrap: 'wrap',
            gap: 10,
            marginTop: 32,
          }}
        >
          <Pill>DAG orchestration</Pill>
          <Pill accent={COLORS.violet}>.sqad Agent Store</Pill>
          <Pill accent={COLORS.green}>Local-first</Pill>
        </div>

        <div
          style={{
            ...staggeredEntrance(frame, 0, 44, fps),
            display: 'inline-flex',
            alignItems: 'center',
            gap: 12,
            marginTop: 38,
            borderRadius: 14,
            padding: '13px 19px',
            color: COLORS.ink,
            background: `linear-gradient(90deg, ${COLORS.cyan}, #8DF4FF)`,
            boxShadow: `0 10px 34px rgba(39,214,245,0.24)`,
            fontWeight: 800,
            fontSize: 16,
            letterSpacing: 0.5,
          }}
        >
          <span style={{fontSize: 18}}>▶</span>
          20-SECOND PRODUCT TOUR
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          right: 102,
          top: 160,
          width: 390,
          height: 390,
          display: 'grid',
          placeItems: 'center',
        }}
      >
        {[1, 2, 3].map((ring) => (
          <div
            key={ring}
            style={{
              position: 'absolute',
              width: 118 + ring * 84,
              height: 118 + ring * 84,
              borderRadius: '50%',
              border: `1px solid ${ring === 2 ? 'rgba(39,214,245,0.33)' : 'rgba(154, 131, 255, 0.2)'}`,
              transform: `scale(${rings + ring * 0.01}) rotate(${frame * (ring % 2 === 0 ? -0.16 : 0.12)}deg)`,
            }}
          />
        ))}
        <div
          style={{
            position: 'absolute',
            width: 160,
            height: 160,
            borderRadius: 44,
            background: 'radial-gradient(circle at 32% 28%, rgba(120,248,255,0.37), rgba(38, 75, 160, 0.2) 42%, rgba(139,92,246,0.14) 70%)',
            filter: 'blur(2px)',
            boxShadow: '0 0 80px rgba(39,214,245,0.23)',
          }}
        />
        <div
          style={{
            position: 'relative',
            zIndex: 2,
            display: 'grid',
            placeItems: 'center',
            height: 140,
            width: 140,
            borderRadius: 40,
            background: 'linear-gradient(145deg, rgba(20,49,101,0.97), rgba(20,27,70,0.96))',
            border: '1px solid rgba(119,240,255,0.55)',
            boxShadow: '0 22px 65px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12)',
          }}
        >
          <ShieldMark size={88} />
        </div>
        {[0, 1, 2, 3].map((index) => {
          const angle = (Math.PI * 2 * index) / 4 + frame / 90;
          const x = Math.cos(angle) * 178;
          const y = Math.sin(angle) * 178;
          return (
            <Dot
              key={index}
              color={[COLORS.cyan, COLORS.green, COLORS.violet, COLORS.cyanSoft][index]}
              size={9}
              style={{position: 'absolute', transform: `translate(${x}px, ${y}px)`}}
            />
          );
        })}
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 40,
          left: 112,
          fontFamily: 'Arial, Helvetica, sans-serif',
          color: COLORS.muted,
          fontSize: 15,
          fontWeight: 600,
          letterSpacing: 0.4,
        }}
      >
        DAG workflows · safe tool execution · provider-agnostic runtime
      </div>
    </AbsoluteFill>
  );
};

type DagNodeProps = {
  frame: number;
  start: number;
  fps: number;
  index: number;
  role: string;
  task: string;
  status: 'complete' | 'active' | 'queued';
  color: string;
  x: number;
  y: number;
};

const statusForNode = {
  complete: {label: 'COMPLETE', icon: '✓'},
  active: {label: 'RUNNING', icon: '↻'},
  queued: {label: 'QUEUED', icon: '○'},
};

const DagNode = ({
  frame,
  start,
  fps,
  index,
  role,
  task,
  status,
  color,
  x,
  y,
}: DagNodeProps) => {
  const statusConfig = statusForNode[status];
  const activePulse = status === 'active' ? 0.5 + 0.5 * Math.sin(frame / 3) : 1;
  return (
    <GlassPanel
      style={{
        ...staggeredEntrance(frame, start, 20 + index * 7, fps, 28),
        position: 'absolute',
        left: x,
        top: y,
        width: 214,
        height: 118,
        boxSizing: 'border-box',
        padding: '12px 15px',
        borderColor: `${color}${status === 'active' ? 'aa' : '55'}`,
        boxShadow:
          status === 'active'
            ? `0 16px 45px ${color}25, 0 0 0 1px ${color}30 inset`
            : undefined,
      }}
    >
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <span
          style={{
            color,
            fontSize: 12,
            fontFamily: 'Arial, Helvetica, sans-serif',
            fontWeight: 800,
            letterSpacing: 1.2,
          }}
        >
          {role}
        </span>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 21,
            minWidth: 21,
            padding: '0 5px',
            borderRadius: 99,
            color: status === 'queued' ? COLORS.muted : COLORS.ink,
            background: status === 'queued' ? 'rgba(130,144,184,0.15)' : color,
            fontSize: 13,
            fontWeight: 900,
            opacity: status === 'active' ? activePulse : 1,
          }}
        >
          {statusConfig.icon}
        </span>
      </div>
      <div
        style={{
          marginTop: 8,
          color: COLORS.text,
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 16,
          fontWeight: 750,
          lineHeight: 1.1,
        }}
      >
        {task}
      </div>
      <div
        style={{
          marginTop: 7,
          color: status === 'queued' ? COLORS.muted : COLORS.textSoft,
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 10,
          fontWeight: 800,
          letterSpacing: 1.1,
        }}
      >
        {statusConfig.label}
      </div>
    </GlassPanel>
  );
};

const FlowLine = ({
  frame,
  from,
  to,
  delay,
  color = COLORS.cyan,
}: {
  frame: number;
  from: [number, number];
  to: [number, number];
  delay: number;
  color?: string;
}) => {
  const progress = clamp((frame - delay) / 24);
  const dotProgress = ((frame - delay) % 42) / 42;
  const x = from[0] + (to[0] - from[0]) * dotProgress;
  const y = from[1] + (to[1] - from[1]) * dotProgress;
  return (
    <>
      <line
        x1={from[0]}
        y1={from[1]}
        x2={from[0] + (to[0] - from[0]) * progress}
        y2={from[1] + (to[1] - from[1]) * progress}
        stroke={color}
        strokeWidth="2"
        strokeDasharray="5 9"
        opacity="0.58"
      />
      {progress > 0.92 ? <circle cx={x} cy={y} r="5" fill={color} /> : null}
    </>
  );
};

const DagScene = ({frame, fps}: {frame: number; fps: number}) => {
  const start = 95;
  const opacity = sceneOpacity(frame, start, 278, 20);

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          top: 103,
          left: 112,
          right: 112,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={staggeredEntrance(frame, start, 0, fps)}>
          <SceneKicker>Mission control</SceneKicker>
        </div>
        <h2
          style={{
            ...staggeredEntrance(frame, start, 6, fps, 27),
            maxWidth: 1056,
            margin: '15px 0 8px',
            color: COLORS.text,
            fontSize: 46,
            lineHeight: 1.05,
            letterSpacing: -2.1,
            fontWeight: 800,
          }}
        >
          One goal becomes a coordinated plan.
        </h2>
        <p
          style={{
            ...staggeredEntrance(frame, start, 11, fps),
            margin: 0,
            color: COLORS.textSoft,
            fontSize: 20,
            lineHeight: 1.35,
          }}
        >
          The manager maps dependencies, assigns specialists, then executes ready work in parallel waves.
        </p>
      </div>

      <GlassPanel
        style={{
          ...staggeredEntrance(frame, start, 16, fps, 22),
          position: 'absolute',
          left: 112,
          top: 254,
          right: 112,
          height: 424,
          overflow: 'hidden',
          background: 'rgba(8, 16, 39, 0.86)',
        }}
      >
        <div
          style={{
            height: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 22px',
            borderBottom: '1px solid rgba(160,181,255,0.14)',
          }}
        >
          <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
            <span style={{fontSize: 18}}>◎</span>
            <span style={{color: COLORS.textSoft, fontWeight: 800, fontSize: 15, letterSpacing: 0.6}}>
              MISSION: SHIP A PRODUCTION-READY SERVICE
            </span>
          </div>
          <Pill accent={COLORS.violet} style={{padding: '7px 12px', fontSize: 12}}>
            3 PARALLEL WAVES
          </Pill>
        </div>

        <svg
          viewBox="0 0 1056 424"
          preserveAspectRatio="none"
          style={{position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible'}}
        >
          <FlowLine frame={frame} delay={start + 32} from={[421, 132]} to={[294, 186]} color={COLORS.cyan} />
          <FlowLine frame={frame} delay={start + 38} from={[635, 132]} to={[756, 186]} color={COLORS.violet} />
          <FlowLine frame={frame} delay={start + 48} from={[294, 284]} to={[312, 304]} color={COLORS.green} />
          <FlowLine frame={frame} delay={start + 58} from={[756, 284]} to={[746, 304]} color={COLORS.amber} />
          <FlowLine frame={frame} delay={start + 66} from={[526, 353]} to={[532, 353]} color={COLORS.cyan} />
        </svg>

        <DagNode
          frame={frame}
          start={start}
          fps={fps}
          index={0}
          role="ORCHESTRATOR"
          task="Plan the DAG"
          status="complete"
          color={COLORS.cyan}
          x={421}
          y={74}
        />
        <DagNode
          frame={frame}
          start={start}
          fps={fps}
          index={1}
          role="ARCHITECT"
          task="Define the system"
          status="complete"
          color={COLORS.green}
          x={80}
          y={176}
        />
        <DagNode
          frame={frame}
          start={start}
          fps={fps}
          index={2}
          role="RESEARCHER"
          task="Validate options"
          status="complete"
          color={COLORS.violet}
          x={762}
          y={176}
        />
        <DagNode
          frame={frame}
          start={start}
          fps={fps}
          index={3}
          role="DEVELOPER"
          task="Build in isolation"
          status="active"
          color={COLORS.cyan}
          x={312}
          y={294}
        />
        <DagNode
          frame={frame}
          start={start}
          fps={fps}
          index={4}
          role="QA REVIEWER"
          task="Verify the output"
          status="queued"
          color={COLORS.amber}
          x={532}
          y={294}
        />
      </GlassPanel>
    </AbsoluteFill>
  );
};

const CheckRow = ({
  color,
  children,
  frame,
  start,
  index,
  fps,
}: {
  color: string;
  children: ReactNode;
  frame: number;
  start: number;
  index: number;
  fps: number;
}) => (
  <div
    style={{
      ...staggeredEntrance(frame, start, 20 + index * 7, fps),
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginTop: 14,
      color: COLORS.textSoft,
      fontFamily: 'Arial, Helvetica, sans-serif',
      fontSize: 18,
      fontWeight: 600,
    }}
  >
    <span
      style={{
        display: 'grid',
        placeItems: 'center',
        height: 24,
        width: 24,
        borderRadius: 8,
        color: COLORS.ink,
        background: color,
        fontSize: 15,
        fontWeight: 900,
      }}
    >
      ✓
    </span>
    {children}
  </div>
);

const GuardrailScene = ({frame, fps}: {frame: number; fps: number}) => {
  const start = 250;
  const opacity = sceneOpacity(frame, start, 407, 20);
  const commandProgress = clamp((frame - (start + 42)) / 22);
  const approved = frame > start + 84;

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          top: 126,
          left: 112,
          width: 530,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={staggeredEntrance(frame, start, 0, fps)}>
          <SceneKicker>Guardrails by default</SceneKicker>
        </div>
        <h2
          style={{
            ...staggeredEntrance(frame, start, 7, fps, 28),
            margin: '16px 0',
            color: COLORS.text,
            fontSize: 52,
            lineHeight: 1.04,
            letterSpacing: -2.6,
            fontWeight: 800,
          }}
        >
          Autonomy with a{' '}
          <span style={{color: COLORS.violetSoft}}>human safety net.</span>
        </h2>
        <p
          style={{
            ...staggeredEntrance(frame, start, 13, fps),
            margin: '0 0 18px',
            color: COLORS.textSoft,
            fontSize: 21,
            lineHeight: 1.4,
          }}
        >
          SquadOS gives agents room to work — while keeping sensitive actions visible, sandboxed, and reviewable.
        </p>
        <CheckRow color={COLORS.cyan} frame={frame} start={start} index={0} fps={fps}>
          Sandboxed files and command allowlists
        </CheckRow>
        <CheckRow color={COLORS.violet} frame={frame} start={start} index={1} fps={fps}>
          Human checkpoints for destructive tools
        </CheckRow>
        <CheckRow color={COLORS.green} frame={frame} start={start} index={2} fps={fps}>
          Verification gates before work ships
        </CheckRow>
      </div>

      <GlassPanel
        style={{
          ...staggeredEntrance(frame, start, 17, fps, 30),
          position: 'absolute',
          top: 149,
          right: 108,
          width: 497,
          height: 411,
          overflow: 'hidden',
          background: 'rgba(10, 18, 42, 0.94)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: 54,
            padding: '0 18px',
            borderBottom: '1px solid rgba(160,181,255,0.14)',
          }}
        >
          <div style={{display: 'flex', gap: 7}}>
            {[COLORS.red, COLORS.amber, COLORS.green].map((color) => (
              <span key={color} style={{height: 10, width: 10, borderRadius: 99, background: color, opacity: 0.85}} />
            ))}
          </div>
          <span
            style={{
              marginLeft: 14,
              color: COLORS.muted,
              fontFamily: 'monospace',
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            /mission/workspace
          </span>
        </div>
        <div style={{padding: '22px 24px', fontFamily: 'monospace', fontSize: 15, lineHeight: 1.8}}>
          <div style={{color: COLORS.muted}}>agent@SquadOS:~$</div>
          <div
            style={{
              color: COLORS.textSoft,
              opacity: commandProgress,
              transform: `translateX(${interpolate(commandProgress, [0, 1], [-12, 0])}px)`,
            }}
          >
            git commit -m "ship service"
          </div>
          <div style={{height: 16}} />
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 10px',
              color: COLORS.amber,
              background: 'rgba(255,190,85,0.1)',
              border: '1px solid rgba(255,190,85,0.35)',
              borderRadius: 8,
              opacity: clamp((frame - (start + 55)) / 12),
            }}
          >
            <span>⚠</span> destructive tool detected
          </div>
        </div>

        <div
          style={{
            position: 'absolute',
            left: 20,
            right: 20,
            bottom: 20,
            minHeight: 126,
            padding: '15px 17px',
            borderRadius: 16,
            background: approved ? 'rgba(66,215,163,0.11)' : 'rgba(139,92,246,0.13)',
            border: `1px solid ${approved ? 'rgba(66,215,163,0.50)' : 'rgba(139,92,246,0.48)'}`,
            transition: 'none',
          }}
        >
          <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
            <span
              style={{
                color: approved ? COLORS.green : COLORS.violetSoft,
                fontSize: 12,
                fontWeight: 900,
                letterSpacing: 1.3,
              }}
            >
              {approved ? '✓ HUMAN REVIEW COMPLETE' : 'HUMAN REVIEW REQUIRED'}
            </span>
            <span style={{color: COLORS.muted, fontSize: 11, fontWeight: 700}}>INTERRUPT #042</span>
          </div>
          <div style={{marginTop: 10, color: COLORS.text, fontSize: 15, fontWeight: 700}}>
            {approved ? 'Approved — commit can resume safely.' : 'Pause execution and request a verdict.'}
          </div>
          <div
            style={{
              display: 'inline-flex',
              marginTop: 11,
              padding: '5px 9px',
              borderRadius: 7,
              color: approved ? COLORS.ink : COLORS.text,
              background: approved ? COLORS.green : 'rgba(139,92,246,0.28)',
              fontSize: 11,
              fontWeight: 900,
              letterSpacing: 0.8,
            }}
          >
            {approved ? 'APPROVED' : 'AWAITING INPUT'}
          </div>
        </div>
      </GlassPanel>

      <div
        style={{
          ...staggeredEntrance(frame, start, 42, fps),
          position: 'absolute',
          bottom: 69,
          left: 112,
          color: COLORS.muted,
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: 0.35,
        }}
      >
        Work can pause, explain itself, and resume — no blocked process thread required.
      </div>
    </AbsoluteFill>
  );
};

const StoreCard = ({
  frame,
  start,
  fps,
  index,
  title,
  category,
  color,
}: {
  frame: number;
  start: number;
  fps: number;
  index: number;
  title: string;
  category: string;
  color: string;
}) => (
  <GlassPanel
    style={{
      ...staggeredEntrance(frame, start, 38 + index * 7, fps, 22),
      flex: 1,
      minWidth: 0,
      padding: '15px 16px',
      borderColor: `${color}55`,
      background: 'rgba(14, 25, 57, 0.9)',
    }}
  >
    <div style={{display: 'flex', alignItems: 'center', gap: 9}}>
      <span
        style={{
          display: 'grid',
          placeItems: 'center',
          width: 27,
          height: 27,
          borderRadius: 8,
          background: `${color}22`,
          border: `1px solid ${color}66`,
          color,
          fontWeight: 900,
          fontSize: 13,
        }}
      >
        ◈
      </span>
      <span style={{color, fontSize: 10, fontWeight: 900, letterSpacing: 1.1}}>{category}</span>
    </div>
    <div style={{marginTop: 13, color: COLORS.text, fontSize: 16, fontWeight: 780, lineHeight: 1.18}}>{title}</div>
  </GlassPanel>
);

const StoreScene = ({frame, fps}: {frame: number; fps: number}) => {
  const start = 380;
  const opacity = sceneOpacity(frame, start, 523, 20);
  const packageScale = spring({
    frame: Math.max(0, frame - (start + 28)),
    fps,
    config: {damping: 15, stiffness: 100, mass: 0.75},
  });

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          top: 111,
          left: 112,
          right: 112,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={staggeredEntrance(frame, start, 0, fps)}>
          <SceneKicker>Agent Store</SceneKicker>
        </div>
        <h2
          style={{
            ...staggeredEntrance(frame, start, 6, fps, 27),
            margin: '15px 0 8px',
            color: COLORS.text,
            fontSize: 48,
            lineHeight: 1.05,
            letterSpacing: -2.2,
            fontWeight: 800,
          }}
        >
          Build a squad once. Reuse it everywhere.
        </h2>
        <p
          style={{
            ...staggeredEntrance(frame, start, 12, fps),
            margin: 0,
            color: COLORS.textSoft,
            fontSize: 20,
          }}
        >
          Package a complete workflow — agents, tools, assets, and a dependency-aware plan — as a portable <b>.sqad</b> bundle.
        </p>
      </div>

      <GlassPanel
        style={{
          ...staggeredEntrance(frame, start, 18, fps, 22),
          position: 'absolute',
          top: 274,
          left: 112,
          width: 481,
          height: 270,
          padding: 0,
          overflow: 'hidden',
          background: 'rgba(8, 16, 39, 0.92)',
        }}
      >
        <div
          style={{
            padding: '13px 19px',
            borderBottom: '1px solid rgba(160,181,255,0.14)',
            color: COLORS.muted,
            fontFamily: 'monospace',
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          squad.yaml
        </div>
        <div style={{padding: '17px 22px', color: COLORS.textSoft, fontFamily: 'monospace', fontSize: 14, lineHeight: 1.68}}>
          <div><span style={{color: COLORS.violetSoft}}>id</span>: devops-on-call</div>
          <div><span style={{color: COLORS.violetSoft}}>agents</span>:</div>
          <div style={{paddingLeft: 18}}>- role: Incident Responder</div>
          <div style={{paddingLeft: 18}}>- role: Systems Verifier</div>
          <div><span style={{color: COLORS.violetSoft}}>workflow</span>:</div>
          <div style={{paddingLeft: 18}}><span style={{color: COLORS.green}}>tasks</span>: dependency-aware DAG</div>
          <div style={{marginTop: 10, color: COLORS.cyan}}>› python -m squad_os.store.cli build ./squad.yaml</div>
        </div>
      </GlassPanel>

      <div
        style={{
          ...staggeredEntrance(frame, start, 29, fps),
          position: 'absolute',
          top: 346,
          left: 624,
          width: 89,
          textAlign: 'center',
          color: COLORS.cyan,
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 15,
          fontWeight: 900,
        }}
      >
        <div style={{fontSize: 33, lineHeight: 1}}>→</div>
        <div style={{marginTop: 8, color: COLORS.muted, fontSize: 10, letterSpacing: 1.2}}>COMPILE</div>
      </div>

      <div
        style={{
          ...staggeredEntrance(frame, start, 32, fps, 26),
          position: 'absolute',
          top: 285,
          right: 112,
          width: 400,
          height: 250,
          display: 'grid',
          placeItems: 'center',
        }}
      >
        <div
          style={{
            width: 218,
            height: 205,
            padding: 24,
            borderRadius: 28,
            transform: `scale(${interpolate(packageScale, [0, 1], [0.75, 1])}) rotate(${interpolate(packageScale, [0, 1], [-6, -1.5])}deg)`,
            background: 'linear-gradient(145deg, rgba(37, 74, 143, 0.98), rgba(79, 42, 146, 0.98))',
            border: '1px solid rgba(157,238,255,0.65)',
            boxShadow: '0 26px 68px rgba(0,0,0,0.32), 0 0 46px rgba(39,214,245,0.22)',
          }}
        >
          <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
            <ShieldMark size={38} />
            <span style={{color: COLORS.cyanSoft, fontSize: 10, fontWeight: 900, letterSpacing: 1.4}}>READY TO SHARE</span>
          </div>
          <div style={{marginTop: 32, color: COLORS.text, fontSize: 31, fontWeight: 850, letterSpacing: -1}}>.sqad</div>
          <div style={{marginTop: 7, color: COLORS.textSoft, fontSize: 14, fontWeight: 700}}>Reusable agent workflow</div>
          <div style={{marginTop: 20, height: 4, borderRadius: 10, background: `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.green})`}} />
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 112,
          right: 112,
          bottom: 69,
          display: 'flex',
          gap: 14,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <StoreCard frame={frame} start={start} fps={fps} index={0} title="DevOps On-Call" category="RECOVERY" color={COLORS.cyan} />
        <StoreCard frame={frame} start={start} fps={fps} index={1} title="Market Intelligence" category="RESEARCH" color={COLORS.violet} />
        <StoreCard frame={frame} start={start} fps={fps} index={2} title="Conditional Data Pipeline" category="AUTOMATION" color={COLORS.green} />
      </div>
    </AbsoluteFill>
  );
};

const PipelineStep = ({
  frame,
  start,
  fps,
  index,
  title,
  description,
  color,
}: {
  frame: number;
  start: number;
  fps: number;
  index: number;
  title: string;
  description: string;
  color: string;
}) => {
  const current = Math.floor((frame - start) / 17) % 4 === index;
  return (
    <div
      style={{
        ...staggeredEntrance(frame, start, 24 + index * 8, fps, 20),
        position: 'relative',
        width: 228,
        minHeight: 130,
        padding: '20px 18px',
        borderRadius: 18,
        background: current ? `${color}18` : 'rgba(18, 29, 63, 0.78)',
        border: `1px solid ${current ? `${color}aa` : 'rgba(133,163,255,0.2)'}`,
        boxShadow: current ? `0 0 38px ${color}25` : undefined,
      }}
    >
      <div style={{color, fontSize: 11, letterSpacing: 1.4, fontWeight: 900}}>0{index + 1}</div>
      <div style={{marginTop: 11, color: COLORS.text, fontSize: 21, fontWeight: 800}}>{title}</div>
      <div style={{marginTop: 8, color: COLORS.textSoft, fontSize: 14, fontWeight: 600, lineHeight: 1.32}}>{description}</div>
      {current ? (
        <div style={{position: 'absolute', top: 17, right: 17}}>
          <Dot color={color} size={8} />
        </div>
      ) : null}
    </div>
  );
};

const OutroScene = ({frame, fps}: {frame: number; fps: number}) => {
  const start = 496;
  const opacity = sceneOpacity(frame, start, 600, 19);

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          top: 117,
          left: 112,
          right: 112,
          textAlign: 'center',
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={{...staggeredEntrance(frame, start, 0, fps), display: 'flex', justifyContent: 'center'}}>
          <SceneKicker>SquadOS</SceneKicker>
        </div>
        <h2
          style={{
            ...staggeredEntrance(frame, start, 7, fps, 28),
            margin: '16px 0 10px',
            color: COLORS.text,
            fontSize: 61,
            lineHeight: 1.02,
            letterSpacing: -3.2,
            fontWeight: 850,
          }}
        >
          Plan. Parallelize. <span style={{color: COLORS.cyanSoft}}>Verify.</span> Ship.
        </h2>
        <p
          style={{
            ...staggeredEntrance(frame, start, 13, fps),
            margin: 0,
            color: COLORS.textSoft,
            fontSize: 21,
            lineHeight: 1.35,
          }}
        >
          The command center for AI agents that are built to collaborate — and built to be trusted.
        </p>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 154,
          right: 154,
          top: 320,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <PipelineStep frame={frame} start={start} fps={fps} index={0} title="Plan" description="Turn a goal into a DAG." color={COLORS.violet} />
        <span style={{color: COLORS.muted, fontSize: 25, fontWeight: 700}}>→</span>
        <PipelineStep frame={frame} start={start} fps={fps} index={1} title="Parallelize" description="Mobilize the right specialists." color={COLORS.cyan} />
        <span style={{color: COLORS.muted, fontSize: 25, fontWeight: 700}}>→</span>
        <PipelineStep frame={frame} start={start} fps={fps} index={2} title="Verify" description="Gate quality and approvals." color={COLORS.green} />
        <span style={{color: COLORS.muted, fontSize: 25, fontWeight: 700}}>→</span>
        <PipelineStep frame={frame} start={start} fps={fps} index={3} title="Ship" description="Keep a durable record." color={COLORS.amber} />
      </div>

      <div
        style={{
          ...staggeredEntrance(frame, start, 48, fps),
          position: 'absolute',
          bottom: 60,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 13,
          color: COLORS.cyan,
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 20,
          fontWeight: 800,
          letterSpacing: 0.5,
          textShadow: '0 0 22px rgba(39,214,245,0.28)',
        }}
      >
        <ShieldMark size={31} />
        github.com/JOHN-REY-CARLO-A-GEMAO/squad-os
      </div>
    </AbsoluteFill>
  );
};

export const SquadOSShowcase = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{background: COLORS.ink}}>
      <Background frame={frame} />
      <TourHeader frame={frame} />
      <IntroScene frame={frame} fps={fps} />
      <DagScene frame={frame} fps={fps} />
      <GuardrailScene frame={frame} fps={fps} />
      <StoreScene frame={frame} fps={fps} />
      <OutroScene frame={frame} fps={fps} />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 4,
          background: `linear-gradient(90deg, ${COLORS.cyan}, ${COLORS.violet}, ${COLORS.green})`,
          opacity: 0.9,
        }}
      />
    </AbsoluteFill>
  );
};
