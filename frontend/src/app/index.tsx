import { router } from 'expo-router';
import { ScrollView } from 'react-native';

import { TopicList } from '@/components/topic-list';
import { Button, ErrorMessage, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { withTotals } from '@/lib/topics';
import { api } from '@/services/api';

/** Main menu: the top-level topics and the review button. */
export default function HomeScreen() {
  const { data, error, loading, reload } = useApi(api.topics);

  if (loading) return <Loading />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;

  const topics = withTotals(data ?? []);
  const due = topics.reduce((sum, t) => sum + t.due_count, 0);

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: Spacing.two }}>
        <Button
          primary
          title={due ? `Review ${due} due` : 'Review'}
          subtitle={due ? undefined : 'Nothing due — learn new cards'}
          onPress={() => router.push('/review')}
        />
        <TopicList topics={topics} parentId={null} onChanged={reload} />
      </ScrollView>
    </Screen>
  );
}
