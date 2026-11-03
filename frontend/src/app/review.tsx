import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { CardHtml } from '@/components/card-html';
import { Button, ErrorMessage, Label, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { useTheme } from '@/hooks/use-theme';
import { formatInterval } from '@/lib/format';
import { api, ApiError, type Grade } from '@/services/api';

const GRADES: { grade: Grade; label: string }[] = [
  { grade: 1, label: 'Again' },
  { grade: 2, label: 'Hard' },
  { grade: 3, label: 'Good' },
  { grade: 4, label: 'Easy' },
];

/** Milliseconds since some fixed point; only called from effects and event handlers, never while rendering. */
const clock = () => Date.now();

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

/** Show each card's front, reveal the back, grade it, move on. */
export default function ReviewScreen() {
  // Optional: review only this topic and its subtopics
  const { topicId } = useLocalSearchParams<{ topicId?: string }>();
  const load = useCallback(() => api.reviewQueue(topicId ? Number(topicId) : undefined), [topicId]);
  const { data, error, loading, reload } = useApi(load);
  const [position, setPosition] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // When the current card was shown, to measure how long the answer took
  const shownAt = useRef(0);
  useEffect(() => {
    shownAt.current = clock();
  }, [position, loading]);

  if (loading) return <Loading />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;

  const cards = data?.cards ?? [];
  const card = cards[position];

  if (!card) {
    return (
      <Screen>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.three }}>
          <Label size={22}>{cards.length ? 'Session complete 🎉' : 'Nothing to review right now'}</Label>
          {lastResult ? <Label muted>{lastResult}</Label> : null}
          <View style={{ flexDirection: 'row' }}>
            <Button title="Back to topics" onPress={() => router.back()} />
          </View>
        </View>
      </Screen>
    );
  }

  const reveal = () => {
    setRevealed(true);
  };

  const grade = async (value: Grade) => {
    try {
      const result = await api.submitReview(card.id, value, clock() - shownAt.current);
      setLastResult(`Last card: next review in ${formatInterval(new Date(), result.due_at)}`);
      setSubmitError(null);
      setRevealed(false);
      setPosition((p) => p + 1);
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.message : String(e));
    }
  };

  const now = new Date();

  return (
    <Screen>
      <Label muted>
        {card.topic_name} · {position + 1} / {cards.length}
        {card.status === 'new' ? ' · new' : ''}
      </Label>
      <View style={{ flex: 1 }}>
        <CardHtml html={revealed ? card.back_html : card.front_html} />
      </View>
      {submitError ? <Label muted>{submitError}</Label> : null}
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
          <Button primary title="Show answer" onPress={reveal} />
        </View>
      )}
    </Screen>
  );
}
