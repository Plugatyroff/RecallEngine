import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { ReviewCard } from '@/components/review-card';
import { Button, ErrorMessage, Label, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { formatInterval } from '@/lib/format';
import { api } from '@/services/api';

/** A review session: every card in the queue in turn. */
export default function ReviewScreen() {
  // Optional: review only this topic and its subtopics
  const { topicId } = useLocalSearchParams<{ topicId?: string }>();
  const load = useCallback(() => api.reviewQueue(topicId ? Number(topicId) : undefined), [topicId]);
  const { data, error, loading, reload } = useApi(load);
  const [position, setPosition] = useState(0);
  const [lastResult, setLastResult] = useState<string | null>(null);

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
            <Button title="Back" onPress={() => router.back()} />
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ReviewCard
        key={card.id}
        card={card}
        header={
          <Label muted>
            {card.topic_name} · {position + 1} / {cards.length}
          </Label>
        }
        onGraded={(result) => {
          setLastResult(`Last card: next review in ${formatInterval(new Date(), result.due_at)}`);
          setPosition((p) => p + 1);
        }}
      />
    </Screen>
  );
}
