import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { CardHtml } from '@/components/card-html';
import { Button, Label } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { formatInterval } from '@/lib/format';
import { api, ApiError, type Grade, type ReviewResult } from '@/services/api';

const GRADES: { grade: Grade; label: string }[] = [
  { grade: 1, label: 'Again' },
  { grade: 2, label: 'Hard' },
  { grade: 3, label: 'Good' },
  { grade: 4, label: 'Easy' },
];

/** Milliseconds since some fixed point; only called from effects and event handlers, never while rendering. */
const clock = () => Date.now();

export type ReviewableCard = {
  id: number;
  front_html: string;
  back_html: string;
  next_due_by_grade: Record<Grade, string>;
};

/**
 * Reviews one card: shows the front, reveals the back, then submits the chosen grade.
 * Render it with `key={card.id}` so it starts fresh (front side) for every card.
 */
export function ReviewCard({
  card,
  header,
  onGraded,
}: {
  card: ReviewableCard;
  header?: ReactNode;
  onGraded: (result: ReviewResult) => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // When the card was shown, to measure how long the answer took
  const shownAt = useRef(0);
  useEffect(() => {
    shownAt.current = clock();
  }, []);

  const grade = async (value: Grade) => {
    try {
      onGraded(await api.submitReview(card.id, value, clock() - shownAt.current));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };

  const now = new Date();

  return (
    <>
      {header}
      <View style={{ flex: 1 }}>
        <CardHtml html={revealed ? card.back_html : card.front_html} />
      </View>
      {error ? <Label muted>{error}</Label> : null}
      {revealed ? (
        <View style={{ flexDirection: 'row', gap: Spacing.two }}>
          {GRADES.map(({ grade: value, label }) => (
            <GradeButton
              key={value}
              label={label}
              interval={formatInterval(now, card.next_due_by_grade[value])}
              primary={value === 3}
              onPress={() => grade(value)}
            />
          ))}
        </View>
      ) : (
        <View style={{ flexDirection: 'row' }}>
          <Button primary title="Show answer" onPress={() => setRevealed(true)} />
        </View>
      )}
    </>
  );
}

/** A grade button on a single line, e.g. "Good 16d"; the text shrinks rather than wraps on narrow phones. */
function GradeButton({
  label,
  interval,
  primary,
  onPress,
}: {
  label: string;
  interval: string;
  primary: boolean;
  onPress: () => void;
}) {
  const colors = useTheme();
  const foreground = primary ? '#ffffff' : colors.text;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.gradeButton,
        { backgroundColor: primary ? '#208AEF' : colors.backgroundElement, opacity: pressed ? 0.7 : 1 },
      ]}>
      <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.6} style={{ color: foreground, fontSize: 15 }}>
        <Text style={{ fontWeight: '600' }}>{label}</Text>
        <Text style={{ fontSize: 13, opacity: 0.75 }}> {interval}</Text>
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  gradeButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.three,
    paddingHorizontal: Spacing.one,
    borderRadius: 10,
  },
});
