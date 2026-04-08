import { ImageResponse } from 'next/og';
import { appIconColors } from '@/lib/chartTheme';

export const size = { width: 32, height: 32 };
export const contentType = 'image/png';

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 6,
          background: appIconColors.canvas,
          color: appIconColors.foreground,
          fontSize: 18,
          fontWeight: 700,
          fontFamily: 'system-ui',
        }}
      >
        A
      </div>
    ),
    { ...size }
  );
}
